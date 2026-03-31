# Run the Flask development server with full logging to server.log
#
# Usage (PowerShell):
#   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
#   . .\.venv\Scripts\Activate.ps1
#   .\run_server.ps1
#
# The script activates the virtual environment (if found), sets FLASK_ENV,
# starts the server and simultaneously writes output to server.log.

param(
    [string]$AppFile  = "app.py",
    [string]$LogFile  = "server.log",
    [string]$Host     = "127.0.0.1",
    [string]$Port     = "5000"
)

# Activate virtual environment if it exists
$venvPaths = @(".\.venv\Scripts\Activate.ps1", ".\venv\Scripts\Activate.ps1")
foreach ($vp in $venvPaths) {
    if (Test-Path $vp) {
        Write-Host "[INFO] Activating virtual environment: $vp"
        . $vp
        break
    }
}

# Load .env variables if python-dotenv is available (best-effort)
if (Test-Path ".env") {
    Write-Host "[INFO] Loading environment variables from .env"
    Get-Content ".env" | ForEach-Object {
        if ($_ -match "^\s*([^#=]+)=(.*)$") {
            $name  = $Matches[1].Trim()
            $value = $Matches[2].Trim()
            [System.Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
}

$env:FLASK_APP = $AppFile
$env:FLASK_ENV = "development"
$env:FLASK_DEBUG = "1"

Write-Host "[INFO] Starting Flask server — output will be logged to $LogFile"
Write-Host "[INFO] URL: http://${Host}:${Port}"
Write-Host "[INFO] Press Ctrl+C to stop."
Write-Host ""

# Run with Tee-Object so output goes to both console and log file
python -u $AppFile 2>&1 | Tee-Object -FilePath $LogFile
