@echo off
setlocal
set "SCRIPT=%~dp0md2html.py"

if "%~1"=="" goto :batch

where py >nul 2>nul
if errorlevel 1 goto :try_python
py -3 "%SCRIPT%" %*
goto :done

:try_python
where python >nul 2>nul
if errorlevel 1 goto :try_python3
python "%SCRIPT%" %*
goto :done

:try_python3
where python3 >nul 2>nul
if errorlevel 1 goto :no_python
python3 "%SCRIPT%" %*
goto :done

:batch
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (where python >nul 2>nul && set "PY=python")
if not defined PY (where python3 >nul 2>nul && set "PY=python3")
if not defined PY goto :no_python

set "count=0"
set "found="
for %%f in ("%~dp0*.md") do (
    set "found=1"
    call :convert "%%f"
)
if not defined found (
    echo ERROR: no .md files found in %~dp0 1>&2
    set "exit_code=1"
    goto :done
)
echo Batch conversion done: %count% .md file(s)
if not defined exit_code set "exit_code=0"
goto :done

:convert
%PY% "%SCRIPT%" %1
if errorlevel 1 set "exit_code=1"
set /a count+=1
goto :eof

:no_python
echo ERROR: Python 3 not found. Please install Python 3.8+ and add it to PATH. 1>&2
set "exit_code=1"

:done
if not defined exit_code set "exit_code=%errorlevel%"
echo %cmdcmdline% | findstr /i /c:"%~f0" >nul && pause
exit /b %exit_code%
