# Startet NoaToDo immer mit dem projekteigenen venv, egal von wo aus aufgerufen.
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
& "$here\venv\Scripts\python.exe" "$here\main.py"
