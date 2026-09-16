@echo off
rem Start VECTOR -- double-click this file.
rem
rem The first time, it creates the .venv folder and installs what VECTOR
rem needs, which takes a few minutes and an internet connection. After
rem that it starts straight away, and installs again only when
rem requirements.txt changes -- after an update, say.
rem
rem VECTOR runs while this window is open. Close the window to stop it.
rem Arguments are passed through, so a shortcut whose target ends in
rem     "Start VECTOR.bat" --lan
rem opens it to the local network.
rem
rem Written with goto rather than if ( ... ) blocks: cmd expands %VARS%
rem when it reads a whole block, so a variable set inside one reads as
rem empty until the block has finished.

setlocal
cd /d "%~dp0"
title VECTOR

set "VENV_PY=.venv\Scripts\python.exe"
set "INSTALLED=.venv\requirements.installed"

if exist "%VENV_PY%" goto :install
echo Setting up VECTOR for the first time. This takes a few minutes...
call :find_python || goto :no_python
%PYTHON_CMD% -m venv .venv || goto :venv_failed

:install
rem A copy of requirements.txt is kept once it has installed, so an update
rem that changes the requirements installs them before VECTOR starts.
fc /b requirements.txt "%INSTALLED%" >nul 2>&1 && goto :run
echo Installing the packages VECTOR needs...
"%VENV_PY%" -m pip install --disable-pip-version-check -r requirements.txt || goto :install_failed
copy /y requirements.txt "%INSTALLED%" >nul

:run
"%VENV_PY%" main.py %*
if errorlevel 1 goto :failed
exit /b 0


:find_python
rem "py" is the launcher python.org installs. A bare "python" may be the
rem Microsoft Store placeholder, which fails the version check below.
for %%P in ("py -3" "python") do (
    %%~P -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>&1 && (
        set "PYTHON_CMD=%%~P"
        exit /b 0
    )
)
exit /b 1

:no_python
echo.
echo Python 3.10 or newer is needed and was not found.
echo Install it from https://www.python.org/downloads/windows/
echo and tick "Add python.exe to PATH" on the first screen of the installer.
pause
exit /b 1

:venv_failed
echo.
echo Could not create the .venv folder. The message above says why.
pause
exit /b 1

:install_failed
echo.
echo Installing the packages failed. Check the internet connection and try again.
echo See "Troubleshooting" in README.md.
pause
exit /b 1

:failed
echo.
echo VECTOR stopped with an error. The message above says why.
echo See "Troubleshooting" in README.md.
pause
exit /b 1
