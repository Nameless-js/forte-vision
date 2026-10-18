$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$cli=Join-Path $projectRoot 'node_modules/.bin/supabase.cmd'
if(-not (Test-Path -LiteralPath $cli)){throw 'Сначала выполните npm install'}
$ErrorActionPreference='Continue'
$statusOutput=& $cli status -o json 2>$null
$statusExit=$LASTEXITCODE
$ErrorActionPreference='Stop'
if($statusExit -ne 0){throw 'Supabase не запущен. Запустите Docker Desktop и npm run db:start'}
$status=$statusOutput | Out-String | ConvertFrom-Json
if($status.result){$status=$status.result}
$apiUrl=$status.API_URL
if(-not $apiUrl){$apiUrl=$status.api_url}
$secret=$status.SECRET_KEY
if(-not $secret){$secret=$status.SERVICE_ROLE_KEY}
if(-not $secret){$secret=$status.secret_key}
if(-not $apiUrl -or -not $secret){throw 'CLI не вернул URL или серверный ключ. Проверьте supabase status локально.'}
$envFile=Join-Path $projectRoot '.env'
$apiKey=$null
if(Test-Path -LiteralPath $envFile){$existing=Get-Content -LiteralPath $envFile;foreach($line in $existing){if($line -match '^API_KEY=(.+)$'){$apiKey=$Matches[1]}}}
if(-not $apiKey){$randomBytes=New-Object byte[] 32;$rng=[Security.Cryptography.RandomNumberGenerator]::Create();$rng.GetBytes($randomBytes);$rng.Dispose();$apiKey=[BitConverter]::ToString($randomBytes).Replace('-','').ToLowerInvariant()}
[IO.File]::WriteAllLines($envFile,@("API_KEY=$apiKey",'DATABASE_BACKEND=supabase',"SUPABASE_URL=$apiUrl","SUPABASE_SECRET_KEY=$secret"),(New-Object Text.UTF8Encoding($false)))
Write-Output 'Локальный Supabase настроен. Секреты сохранены только в игнорируемом .env.'
Write-Output 'Перезапустите Python API и Vite, чтобы применить конфигурацию.'
