param(
    [Parameter(Mandatory = $true)]
    [string]$ApiToken,

    [string]$AppName = "factory-shift-bot",
    [string]$DbName = "factory-shift-db",
    [string]$NetworkName = "factory-shift-net",
    [string]$AppPlan = "small-g2",
    [string]$FeaturePlan = "basic",
    [string]$DbPlan = "small-g2",
    [string]$DbVersion = "15",
    [string]$WebhookSecret = "",
    [string]$BaleBotToken = ""
)

$ErrorActionPreference = "Stop"

function Run-Liara {
    param([string[]]$Arguments)
    & liara @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Liara command failed: liara $($Arguments -join ' ')"
    }
}

Write-Host "Checking Liara CLI..."
& liara --version

Write-Host "Creating network if needed..."
& liara network create --api-token $ApiToken --name $NetworkName
if ($LASTEXITCODE -ne 0) {
    Write-Host "Network may already exist. Continuing..."
}

Write-Host "Creating PostgreSQL database if needed..."
& liara db create --api-token $ApiToken --name $DbName --type postgres --version $DbVersion --plan $DbPlan --feature-plan $FeaturePlan --network $NetworkName --yes
if ($LASTEXITCODE -ne 0) {
    Write-Host "Database may already exist or account plan may block creation. Continuing..."
}

Write-Host "Creating app if needed..."
& liara create --api-token $ApiToken --app $AppName --platform docker --plan $AppPlan --feature-plan $FeaturePlan --network $NetworkName
if ($LASTEXITCODE -ne 0) {
    Write-Host "App may already exist or account plan may block creation. Continuing to deploy..."
}

$envArgs = @(
    "APP_NAME=Factory Shift",
    "SQLALCHEMY_ECHO=false",
    "AUTO_CREATE_TABLES=false",
    "DEFAULT_BOT_PLATFORM=bale",
    "BALE_API_BASE_URL=https://tapi.bale.ai"
)

if ($WebhookSecret.Trim().Length -gt 0) {
    $envArgs += "BOT_WEBHOOK_SECRET=$WebhookSecret"
}

if ($BaleBotToken.Trim().Length -gt 0) {
    $envArgs += "BALE_BOT_TOKEN=$BaleBotToken"
}

Write-Host "Setting non-database environment variables..."
Run-Liara (@("env", "set") + $envArgs + @("--api-token", $ApiToken, "--app", $AppName, "--force"))

Write-Host "Deploying Docker app..."
Run-Liara @("deploy", "--api-token", $ApiToken, "--app", $AppName, "--platform", "docker", "--port", "8000", "--path", ".", "--build-location", "germany")

Write-Host "Done. Set DATABASE_URL from Liara database connection string if it was not set automatically."
Write-Host "Then run migrations in Liara shell:"
Write-Host "  liara shell --api-token <TOKEN> --app $AppName"
Write-Host "  python -m alembic upgrade head"
Write-Host "  python tools/seed_mvp.py"
