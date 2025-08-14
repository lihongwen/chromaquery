# PowerShell脚本推送代码到GitHub
Write-Host "开始推送代码到远程仓库..." -ForegroundColor Green

# 设置工作目录
Set-Location "C:\Users\10623\Documents\augment-projects\chromaquery"

try {
    Write-Host "检查Git状态..." -ForegroundColor Yellow
    & git status --short
    
    Write-Host "添加所有文件到暂存区..." -ForegroundColor Yellow
    & git add .
    
    Write-Host "提交更改..." -ForegroundColor Yellow
    & git commit -m "推送ChromaQuery项目代码到GitHub仓库 - 包含后端API、前端界面和文档"
    
    Write-Host "推送到远程仓库..." -ForegroundColor Yellow
    & git push -u origin main
    
    Write-Host "推送成功完成！" -ForegroundColor Green
    Write-Host "您的代码已成功推送到: https://github.com/lihongwen/chromaquery.git" -ForegroundColor Cyan
}
catch {
    Write-Host "错误: $_" -ForegroundColor Red
}

Write-Host "按任意键继续..."
Read-Host