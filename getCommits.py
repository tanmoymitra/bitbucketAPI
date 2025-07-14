import requests
from collections import defaultdict
from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# 🔐 Auth & Config
USERNAME = 'your_username'
APP_PASSWORD = 'your_app_password'
WORKSPACE = 'your_workspace'
auth = HTTPBasicAuth(USERNAME, APP_PASSWORD)

# 📅 Date filters
today = datetime.utcnow()
days_back = 30
repo_updated_after = today - timedelta(days=days_back)
commit_start_date = today - timedelta(days=30)
commit_end_date = today

# 🧾 Get updated repos
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

# 🔁 Process one repo: return user commit stats
def process_repo(repo_slug):
    print(f"🔍 Processing repo: {repo_slug}")
    user_stats = defaultdict(lambda: {"commits": 0, "additions": 0, "deletions": 0})
    commits_url = f"https://api.bitbucket.org/2.0/repositories/{WORKSPACE}/{repo_slug}/commits"

    while commits_url:
        resp = requests.get(commits_url, auth=auth)
        if resp.status_code != 200:
            print(f"❌ Failed to fetch commits for {repo_slug}")
            break

        data = resp.json()
        for commit in data.get('values', []):
            commit_date = datetime.fromisoformat(commit['date'][:-6])
            if not (commit_start_date <= commit_date <= commit_end_date):
                continue

            author = commit['author'].get('user', {}).get('display_name') or commit['author']['raw']
            commit_hash = commit['hash']
            user_stats[author]["commits"] += 1

            # Get diffstat (lines added/deleted)
            diff_url = f"https://api.bitbucket.org/2.0/repositories/{WORKSPACE}/{repo_slug}/diffstat/{commit_hash}"
            diff_resp = requests.get(diff_url, auth=auth)
            if diff_resp.status_code == 200:
                for file in diff_resp.json().get('values', []):
                    user_stats[author]["additions"] += file.get('lines_added', 0)
                    user_stats[author]["deletions"] += file.get('lines_removed', 0)

        commits_url = data.get('next')

    return repo_slug, user_stats

# ▶️ Main logic
if __name__ == "__main__":
    print(f"📆 Fetching repos updated in the last {days_back} days...")
    recent_repos = get_recent_repos()
    print(f"✅ Found {len(recent_repos)} repositories.")

    repo_results = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_repo = {executor.submit(process_repo, repo): repo for repo in recent_repos}
        for future in as_completed(future_to_repo):
            repo_slug, user_data = future.result()
            repo_results[repo_slug] = user_data

    # 📊 Final Output
    print("\n📊 Repo-wise Commit Summary (last 30 days):")
    for repo, users in repo_results.items():
        print(f"\n📁 Repo: {repo}")
        if not users:
            print("  No commits.")
            continue
        for user, data in sorted(users.items(), key=lambda x: x[1]['commits'], reverse=True):
            print(f"  {user}: {data['commits']} commits, +{data['additions']} / -{data['deletions']}")

    # 🔁 Overall Summary (Optional)
    overall = defaultdict(lambda: {"commits": 0, "additions": 0, "deletions": 0})
    for users in repo_results.values():
        for user, stats in users.items():
            overall[user]["commits"] += stats["commits"]
            overall[user]["additions"] += stats["additions"]
            overall[user]["deletions"] += stats["deletions"]

    print("\n📦 Overall Totals:")
    for user, data in sorted(overall.items(), key=lambda x: x[1]['commits'], reverse=True):
        print(f"{user}: {data['commits']} commits, +{data['additions']} / -{data['deletions']}")
