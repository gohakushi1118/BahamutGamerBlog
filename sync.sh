#!/bin/sh
# Runs INSIDE the Linux container (python:3.12-slim) from the Jenkins pipeline.
# Clones the repo fresh, scrapes, commits and pushes — entirely within the
# container's own filesystem, so nothing is written back to a bind mount
# (a Windows Docker host makes the mounted workspace read-only to the container).
#
# Required env vars (passed via `docker run -e`):
#   OWNER, BRANCH, GH_USER, GH_TOKEN, ORIGIN_URL
set -e

apt-get update -qq && apt-get install -y -qq git >/dev/null

# Normalise the origin URL (supports https:// and git@) into host/path form.
REPO=$(printf '%s' "$ORIGIN_URL" | sed -E 's#^git@([^:]+):#\1/#; s#^https?://([^/@]+@)?##')

git clone --depth 1 -b "$BRANCH" "https://$GH_USER:$GH_TOKEN@$REPO" /repo
cd /repo

pip install --quiet --root-user-action=ignore -r requirements.txt
python scraper.py --owner "$OWNER" --out .

git config user.email "bot@users.noreply.github.com"
git config user.name  "baha-blog-bot"
git add -A
if git diff --cached --quiet; then
    echo "No changes detected, skipping commit."
else
    git commit -m "chore: sync Bahamut creations ($OWNER) $(date +%F)"
    git push origin "HEAD:$BRANCH"
fi
