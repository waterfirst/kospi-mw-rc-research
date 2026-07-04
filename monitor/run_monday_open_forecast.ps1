$ErrorActionPreference = "Continue"
$repo = "D:\nakcho\python\kospi-mw-rc-research"
Set-Location $repo
$env:GIT_TERMINAL_PROMPT = "0"
python monitor\overnight_0730_strategy.py --now --glm --telegram
python monitor\forecast_watchdog.py --kind open --label 0730 --glm --telegram
git add contest/overnight contest/news contest/learning monitor HOME_SERVER_SETUP.md SERVER_MONITORING_PLAN.md
git commit -m "Record 2026-07-06 open forecast" 2>$null
git fetch https://waterfirst@github.com/waterfirst/kospi-mw-rc-research.git master
git rebase FETCH_HEAD
git push https://waterfirst@github.com/waterfirst/kospi-mw-rc-research.git master
