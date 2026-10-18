$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$cli=Join-Path $projectRoot 'node_modules/.bin/supabase.cmd'
if(-not (Test-Path -LiteralPath $cli)){throw 'Сначала выполните npm install'}
# Capture startup output because Supabase prints secret keys on successful startup.
$ErrorActionPreference='Continue'
$startup=& $cli start --exclude realtime,storage-api,imgproxy,mailpit,edge-runtime,logflare,vector,supavisor 2>&1
$startupExit=$LASTEXITCODE
$ErrorActionPreference='Stop'
if($startupExit -ne 0){throw 'Не удалось запустить Supabase. Проверьте, что Docker Desktop работает.'}
& (Join-Path $PSScriptRoot 'configure-local.ps1')
