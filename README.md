# bitbucketAPI

Here's a fully upgraded version of the Bitbucket analytics script that:<br/>
✅ Features:<br/>
&nbsp;&nbsp;&nbsp;&nbsp;✅ Filters repositories updated in the last 30 days<br/>
&nbsp;&nbsp;&nbsp;&nbsp;✅ Counts commits, additions, deletions per user<br/>
&nbsp;&nbsp;&nbsp;&nbsp;✅ Breaks down data per repository<br/>
&nbsp;&nbsp;&nbsp;&nbsp;✅ Runs in parallel using concurrent.futures for speed<br/>
<br/>
# Performance Tips:
&nbsp;&nbsp;&nbsp;&nbsp;✅ max_workers=5 → Adjust to your system or API rate limits.<br/>
&nbsp;&nbsp;&nbsp;&nbsp;✅ For large teams, consider caching diff results or using batch mode.<br/>