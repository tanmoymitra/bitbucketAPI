# bitbucketAPI
</br>
Here’s the enhanced final version of the script that:</br>

✅ Scans all branches of all recently updated repos</br>
✅ Excludes merge commits</br>
✅ Counts commits + lines added/deleted per user</br>
✅ Adds branch-wise details for full auditing</br>
✅ Exports to Excel with three sheets:</br>
 - Repo-wise Summary (aggregated per repo + user)</br>
 - Overall Summary (aggregated per user across all repos)</br>
 - Branch-wise Details (per repo + branch + user for auditing)</br>
<br/>
# Performance Tips:</br>
&nbsp;&nbsp;&nbsp;&nbsp;✅ max_workers=5 → Adjust to your system or API rate limits.<br/>
&nbsp;&nbsp;&nbsp;&nbsp;✅ For large teams, consider caching diff results or using batch mode.<br/>
