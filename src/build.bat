@echo off
rem NoaToDo, a local encrypted to-do app for Windows.
rem Copyright (C) 2026 Noa Gnos
rem
rem This program is free software: you can redistribute it and/or modify
rem it under the terms of the GNU General Public License as published by
rem the Free Software Foundation, either version 3 of the License, or
rem (at your option) any later version.
rem
rem This program is distributed in the hope that it will be useful,
rem but WITHOUT ANY WARRANTY; without even the implied warranty of
rem MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
rem GNU General Public License for more details.
rem
rem You should have received a copy of the GNU General Public License
rem along with this program.  If not, see <https://www.gnu.org/licenses/>.

rem Baut NoaToDo.exe, egal von wo aus aufgerufen (Doppelklick oder Konsole).
rem Immer mit dem projekteigenen venv, wie run.ps1 fuer den Start der App.
rem Argumente werden durchgereicht:  build.bat --onedir --console
setlocal
set "HERE=%~dp0"
set "PY=%HERE%venv\Scripts\python.exe"

if not exist "%PY%" (
    echo.
    echo Kein venv gefunden unter: %PY%
    echo Erst die Umgebung anlegen, dann erneut bauen:
    echo   python -m venv venv
    echo   venv\Scripts\python.exe -m pip install -r requirements.lock.hashes.txt --require-hashes
    echo   venv\Scripts\python.exe -m pip install -r requirements-dev.txt
    set "EXITCODE=1"
    goto :ende
)

"%PY%" "%HERE%tools\build_exe.py" %*
set "EXITCODE=%ERRORLEVEL%"

:ende
rem Beim Doppelklick startet der Explorer die Datei als "cmd /c ...", und das
rem Fenster wuerde sich am Ende sofort schliessen: dann waeren gerade die
rem wichtigen Zeilen weg (Pfad der .exe, Groesse, die beiden Hinweise zu
rem Signatur und WebView2-Runtime). Deshalb hier warten. Aus einer schon
rem offenen Konsole wird nicht gewartet, und NOATODO_NOPAUSE=1 schaltet das
rem Warten fuer Automatisierung ganz ab.
if defined NOATODO_NOPAUSE goto :raus
echo %CMDCMDLINE% | find /i "/c" >nul && pause

:raus
exit /b %EXITCODE%
