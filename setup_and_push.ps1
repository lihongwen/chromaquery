# Complete Git setup and push script
Write-Host "=== ChromaQuery Project Push to GitHub ===" -ForegroundColor Cyan

# Set working directory
Set-Location "C:\Users\10623\Documents\augment-projects\chromaquery"

# Configure Git user information
Write-Host "Configuring Git user information..." -ForegroundColor Yellow
& git config user.name "lihongwen"
& git config user.email "lihongwen@users.noreply.github.com"

# Check current status
Write-Host "Checking repository status..." -ForegroundColor Yellow
& git status

# Add all files
Write-Host "Adding files to staging area..." -ForegroundColor Yellow
& git add .

# Check if there are changes to commit
$status = & git status --porcelain
if ($status) {
    Write-Host "Committing changes..." -ForegroundColor Yellow
    & git commit -m "Initial commit: ChromaQuery vector database query system

- Add backend API server and database integration
- Add React frontend user interface  
- Include ChromaDB configuration and management tools
- Add documentation and configuration files
- Support multiple embedding models and LLM integration"
} else {
    Write-Host "No changes to commit" -ForegroundColor Green
}

# Push to remote repository
Write-Host "Pushing to GitHub..." -ForegroundColor Yellow
& git push -u origin main

Write-Host "Push completed! Your project is now available at:" -ForegroundColor Green
Write-Host "https://github.com/lihongwen/chromaquery" -ForegroundColor Cyan

# Clean up temporary script files
Write-Host "Cleaning up temporary files..." -ForegroundColor Yellow
Remove-Item "push_to_repo.bat" -ErrorAction SilentlyContinue
Remove-Item "git_push.ps1" -ErrorAction SilentlyContinue
Remove-Item "setup_and_push.ps1" -ErrorAction SilentlyContinue

Write-Host "Completed!" -ForegroundColor Green