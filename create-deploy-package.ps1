# Script to create deployment package for Appwrite Functions

Write-Host "Creating Appwrite deployment package..." -ForegroundColor Green

# Create deployment directory
$deployDir = "appwrite-deploy"
if (Test-Path $deployDir) {
    Remove-Item -Recurse -Force $deployDir
}
New-Item -ItemType Directory -Path $deployDir | Out-Null

# Copy required files
Write-Host "Copying files..." -ForegroundColor Yellow
Copy-Item "main.py" -Destination $deployDir
Copy-Item "requirements.txt" -Destination $deployDir
Copy-Item "README.md" -Destination $deployDir -ErrorAction SilentlyContinue
Copy-Item "APPWRITE.md" -Destination $deployDir -ErrorAction SilentlyContinue

# Create zip file
Write-Host "Creating zip archive..." -ForegroundColor Yellow
$zipPath = "qr-microservice-appwrite.zip"
if (Test-Path $zipPath) {
    Remove-Item -Force $zipPath
}

Compress-Archive -Path "$deployDir\*" -DestinationPath $zipPath

# Cleanup
Remove-Item -Recurse -Force $deployDir

Write-Host "`n✅ Deployment package created: $zipPath" -ForegroundColor Green
Write-Host "`nFiles included:" -ForegroundColor Cyan
Write-Host "  - main.py" -ForegroundColor White
Write-Host "  - requirements.txt" -ForegroundColor White
Write-Host "  - README.md (if exists)" -ForegroundColor White
Write-Host "  - APPWRITE.md (if exists)" -ForegroundColor White

Write-Host "`nNext steps:" -ForegroundColor Yellow
Write-Host "1. Go to Appwrite Console -> Functions" -ForegroundColor White
Write-Host "2. Create new function (Python 3.11)" -ForegroundColor White
Write-Host "3. Set timeout to 30 seconds" -ForegroundColor White
Write-Host "4. Upload $zipPath" -ForegroundColor White
Write-Host "5. Set entrypoint: main.py" -ForegroundColor White
Write-Host "6. Deploy!" -ForegroundColor White
