import requests
from collections import defaultdict
from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd

# 🔐 Auth & Config
USERNAME = 'your_username'
APP_PASSWORD = 'your_app_password'
WORKSPACE = 'your_workspace'
auth = HTTPBasicAuth(USERNAME, APP_PASSWORD)

# 📆 Time filters
today = datetime.utcnow()
days_back = 30
commit_start_date = today - timedelta(days=days_back)
commit_end_date = today
repo_updated_after = today - timedelta(days=days_back)

# 🔹 Fetch updated repos
def get_recent_repos():
    repos_url = f"https://api.bitbucket.org/2.0/repositories/{WORKSPACE}?pagelen=50"
    recent_repos = []
    while repos_url:
        resp = requests.get(repos_url, auth=auth)
        data = resp.json()
        for repo in data['values']:
            updated_on = datetime.fromisoformat(repo['updated_on'][:-6])
            if updated_on >= repo_updated_after:
                recent_repos.append(repo['slug'])
        repos_url = data.get('next')
    return recent_repos

# 🔹 Fetch all branches for a repo
def get_branches(repo_slug):
    branches = []
    url = f"https://api.bitbucket.org/2.0/repositories/{WORKSPACE}/{repo_slug}/refs/branches?pagelen=50"
    while url:
        resp = requests.get(url, auth=auth)
        if resp.status_code != 200:
            break
        data = resp.json()
        branches.extend([b['name'] for b in data.get('values', [])])
        url = data.get('next')
    return branches

# 🔹 Process one repo for all branches
def process_repo(repo_slug):
    print(f"🔍 Processing repo: {repo_slug}")
    user_stats = defaultdict(lambda: {"commits": 0, "additions": 0, "deletions": 0})
    branch_stats = defaultdict(lambda: defaultdict(lambda: {"commits": 0, "additions": 0, "deletions": 0}))
    seen_commits = set()

    for branch in get_branches(repo_slug):
        commits_url = f"https://api.bitbucket.org/2.0/repositories/{WORKSPACE}/{repo_slug}/commits/{branch}?pagelen=50"
        while commits_url:
            resp = requests.get(commits_url, auth=auth)
            if resp.status_code != 200:
                print(f"❌ Failed to fetch commits for {repo_slug}:{branch}")
                break

            data = resp.json()
            for commit in data.get('values', []):
                commit_hash = commit['hash']
                if commit_hash in seen_commits:
                    continue
                seen_commits.add(commit_hash)

                # 🚫 Skip merge commits
                if len(commit.get('parents', [])) > 1:
                    continue

                commit_date = datetime.fromisoformat(commit['date'][:-6])
                if not (commit_start_date <= commit_date <= commit_end_date):
                    continue

                author = commit['author'].get('user', {}).get('display_name') or commit['author']['raw']
                user_stats[author]["commits"] += 1
                branch_stats[branch][author]["commits"] += 1

                # Fetch diffstat for lines added/deleted
                diff_url = f"https://api.bitbucket.org/2.0/repositories/{WORKSPACE}/{repo_slug}/diffstat/{commit_hash}"
                diff_resp = requests.get(diff_url, auth=auth)
                if diff_resp.status_code == 200:
                    for file in diff_resp.json().get('values', []):
                        lines_added = file.get('lines_added', 0)
                        lines_removed = file.get('lines_removed', 0)
                        user_stats[author]["additions"] += lines_added
                        user_stats[author]["deletions"] += lines_removed
                        branch_stats[branch][author]["additions"] += lines_added
                        branch_stats[branch][author]["deletions"] += lines_removed

            commits_url = data.get('next')

    return repo_slug, user_stats, branch_stats

# ▶️ Main logic
if __name__ == "__main__":
    recent_repos = get_recent_repos()
    print(f"✅ Found {len(recent_repos)} updated repositories in last {days_back} days.")

    repo_results = {}
    branch_results = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_repo = {executor.submit(process_repo, repo): repo for repo in recent_repos}
        for future in as_completed(future_to_repo):
            repo_slug, user_data, branch_data = future.result()
            repo_results[repo_slug] = user_data
            branch_results[repo_slug] = branch_data

    # 📊 Prepare Repo-wise DataFrame
    repo_rows = []
    for repo, users in repo_results.items():
        for user, stats in users.items():
            repo_rows.append({
                "Repository": repo,
                "User": user,
                "Commits": stats["commits"],
                "Lines Added": stats["additions"],
                "Lines Deleted": stats["deletions"]
            })
    repo_df = pd.DataFrame(repo_rows)

    # 📊 Prepare Branch-wise DataFrame
    branch_rows = []
    for repo, branches in branch_results.items():
        for branch, users in branches.items():
            for user, stats in users.items():
                branch_rows.append({
                    "Repository": repo,
                    "Branch": branch,
                    "User": user,
                    "Commits": stats["commits"],
                    "Lines Added": stats["additions"],
                    "Lines Deleted": stats["deletions"]
                })
    branch_df = pd.DataFrame(branch_rows)

    # 📊 Overall Summary
    overall = defaultdict(lambda: {"commits": 0, "additions": 0, "deletions": 0})
    for users in repo_results.values():
        for user, stats in users.items():
            overall[user]["commits"] += stats["commits"]
            overall[user]["additions"] += stats["additions"]
            overall[user]["deletions"] += stats["deletions"]

    overall_rows = []
    for user, stats in overall.items():
        overall_rows.append({
            "User": user,
            "Commits": stats["commits"],
            "Lines Added": stats["additions"],
            "Lines Deleted": stats["deletions"]
        })
    overall_df = pd.DataFrame(overall_rows)

    # 💾 Export to Excel
    filename = f"bitbucket_summary_{today.date()}.xlsx"
    with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
        repo_df.to_excel(writer, sheet_name='Repo-wise Summary', index=False)
        branch_df.to_excel(writer, sheet_name='Branch-wise Details', index=False)
        overall_df.to_excel(writer, sheet_name='Overall Summary', index=False)

    print(f"\n✅ Excel report generated: {filename}")
