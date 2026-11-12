@echo off
rem VS Code Marketplace ga chiqarish. Token faqat shu oynada kiritiladi, hech qayerga saqlanmaydi.
rem Oldin: marketplace.visualstudio.com/manage da "akromind" nomli publisher yaratilgan bo'lishi kerak.
cd /d "%~dp0"
set /p PAT=Azure DevOps token (Marketplace: Manage) ni kiriting va Enter bosing:
if "%PAT%"=="" (echo Token kiritilmadi & pause & exit /b 1)
call npx --yes @vscode/vsce@3 publish --packagePath "..\02_tayyor_paketlar\ovoz-kiritish-0.3.4.vsix" -p %PAT%
set PAT=
echo.
echo Tayyor bo'lsa: https://marketplace.visualstudio.com/items?itemName=akromind.ovoz-kiritish (5-10 daqiqadan keyin ko'rinadi)
pause
