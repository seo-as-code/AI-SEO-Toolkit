@echo off
cd /d C:\Users\emami\proyecto_seo\ai-seo-toolkit
echo === Etapa 3 AI SEO === > reports\code\ultimo_run.txt
echo Inicio: %date% %time% >> reports\code\ultimo_run.txt
echo. >> reports\code\ultimo_run.txt
powershell -NoProfile -ExecutionPolicy Bypass -File reports\code\run_etapa3.ps1 >> reports\code\ultimo_run.txt 2>&1
echo. >> reports\code\ultimo_run.txt
echo Fin: %date% %time% >> reports\code\ultimo_run.txt
echo.
echo Listo. Abre en Cursor: ai-seo-toolkit\reports\code\ultimo_run.txt
echo En el chat escribe: @ultimo_run.txt
pause
