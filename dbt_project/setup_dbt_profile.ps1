# dbt Profile Setup Script
# This script copies the profiles.yml.example to the correct location

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "dbt Profile Setup Script" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Define paths
$dbtDir = "$env:USERPROFILE\.dbt"
$profileExample = "$PSScriptRoot\profiles.yml.example"
$profileDest = "$dbtDir\profiles.yml"

# Create .dbt directory if it doesn't exist
if (-not (Test-Path $dbtDir)) {
    Write-Host "Creating .dbt directory at: $dbtDir" -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $dbtDir -Force | Out-Null
}

# Check if profiles.yml already exists
if (Test-Path $profileDest) {
    Write-Host ""
    Write-Host "WARNING: profiles.yml already exists at:" -ForegroundColor Yellow
    Write-Host $profileDest -ForegroundColor White
    Write-Host ""
    $overwrite = Read-Host "Do you want to overwrite it? (y/n)"
    
    if ($overwrite -ne "y") {
        Write-Host "Setup canceled. No changes made." -ForegroundColor Red
        exit
    }
}

# Copy the file
Write-Host ""
Write-Host "Copying profiles.yml to ~/.dbt/ directory..." -ForegroundColor Green
Copy-Item $profileExample $profileDest -Force

Write-Host "✓ File copied successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "IMPORTANT: Next Steps" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Open the file at: $profileDest" -ForegroundColor Yellow
Write-Host "2. Replace 'your_secure_password_here' with your actual PostgreSQL password" -ForegroundColor Yellow
Write-Host "3. Run: dbt debug" -ForegroundColor Yellow
Write-Host ""
Write-Host "Your PostgreSQL password can be found in your .env file" -ForegroundColor White
Write-Host "(Variable: POSTGRES_PASSWORD)" -ForegroundColor White
Write-Host ""
