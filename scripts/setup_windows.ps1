# Windows setup script for SAHI project
# Run this script in a fresh PowerShell session.

# Move to project root
Set-Location "C:\Users\bokin\Downloads\sahi"

# Verify project structure
Write-Host "\n--- PROJECT CHECK ---"
$hasPyproject = Test-Path .\pyproject.toml
$hasSrc = Test-Path .\src\sahi
$hasDemo = Test-Path .\src\sahi\demo\__main__.py
Write-Host "pyproject.toml: $hasPyproject"
Write-Host "src/sahi: $hasSrc"
Write-Host "demo entrypoint: $hasDemo"

# Create virtual environment if missing
if (-not (Test-Path .\.venv\Scripts\python.exe)) {
    py -3.13 -m venv .venv
    Write-Host ".venv created"
} else {
    Write-Host ".venv already exists"
}

# Upgrade pip
.\.venv\Scripts\python.exe -m pip install --upgrade pip

# Install the project in editable mode
.\.venv\Scripts\python.exe -m pip install -e .

# Install test tools
.\.venv\Scripts\python.exe -m pip install pytest pytest-cov

# Verify Python version
.\.venv\Scripts\python.exe --version

# Run verification commands (no live API calls)
Write-Host "\n--- TEST COLLECTION ---"
.\.venv\Scripts\python.exe -m pytest --collect-only -q
Write-Host "\n--- FULL TESTS ---"
.\.venv\Scripts\python.exe -m pytest -v
Write-Host "\n--- COVERAGE ---"
.\.venv\Scripts\python.exe -m pytest --cov=sahi --cov-report=term-missing
Write-Host "\n--- LOCAL DEMO ---"
.\.venv\Scripts\python.exe -m sahi.demo

# Check FFmpeg usage (optional)
Write-Host "\n--- FFmpeg REFERENCE CHECK ---"
Get-ChildItem .\src -Recurse -Filter *.py | Select-String -Pattern "ffmpeg"

# Verify SARVAM API key presence (do not display value)
Write-Host "\n--- SARVAM API KEY CHECK ---"
$hasKey = [bool]$env:SARVAM_API_KEY
Write-Host "API key present: $hasKey"
