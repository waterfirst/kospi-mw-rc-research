#!/usr/bin/env bash
# phone_server/pages/ 를 gh-pages 브랜치로 배포 → 공개 GitHub Pages 링크 갱신.
# (남한테 카톡 등으로 공유하는 공개 HTTPS 링크용. 폰서버 배포는 sync.sh 참고)
# 사용:  bash phone_server/publish_pages.sh
set -e
REPO="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
cd "$REPO"
git worktree remove -f "$TMP" 2>/dev/null || true
git branch -D ghp-tmp 2>/dev/null || true
git worktree add -f -b ghp-tmp "$TMP" HEAD >/dev/null
cd "$TMP"
git rm -rqf . >/dev/null 2>&1 || true
cp -r "$REPO/phone_server/pages/"* .
touch .nojekyll                 # Jekyll 처리 끄기(_ 폴더/에셋 그대로 서빙)
git add -A
git commit -qm "GitHub Pages 배포: $(date '+%F %T')" || { echo "변경 없음"; }
git push -f origin ghp-tmp:gh-pages
cd "$REPO"; git worktree remove -f "$TMP"; git branch -D ghp-tmp
echo "공개 링크 → https://waterfirst.github.io/kospi-mw-rc-research/spain-trip.html"
