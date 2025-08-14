@echo off
echo 开始推送代码到远程仓库...
echo.

echo 检查Git状态...
git status

echo.
echo 添加所有文件到暂存区...
git add .

echo.
echo 提交更改...
git commit -m "推送项目代码到GitHub仓库"

echo.
echo 推送到远程仓库...
git push -u origin main

echo.
echo 推送完成！
pause