@echo off
setlocal
set "SCRIPT=%~dp0md2html.py"

where py >nul 2>nul
if errorlevel 1 goto :try_python
py -3 "%SCRIPT%" %*
exit /b %errorlevel%

:try_python
where python >nul 2>nul
if errorlevel 1 goto :try_python3
python "%SCRIPT%" %*
exit /b %errorlevel%

:try_python3
where python3 >nul 2>nul
if errorlevel 1 goto :no_python
python3 "%SCRIPT%" %*
exit /b %errorlevel%

:no_python
echo ERROR: Python 3 not found. Please install Python 3.8+ and add it to PATH. 1>&2
exit /b 1
