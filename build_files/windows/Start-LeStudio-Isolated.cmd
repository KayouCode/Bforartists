@echo off
setlocal
set "APPDATA=%LOCALAPPDATA%\LeStudioFork\Roaming"
set "BLENDER_USER_RESOURCES=%LOCALAPPDATA%\LeStudioFork\resources"
set "BLENDER_USER_CONFIG=%LOCALAPPDATA%\LeStudioFork\config"
set "BLENDER_USER_SCRIPTS=%LOCALAPPDATA%\LeStudioFork\scripts"
set "BLENDER_USER_EXTENSIONS=%LOCALAPPDATA%\LeStudioFork\extensions"
set "BLENDER_USER_DATAFILES=%LOCALAPPDATA%\LeStudioFork\datafiles"
if not exist "%BLENDER_USER_CONFIG%" mkdir "%BLENDER_USER_CONFIG%"
if not exist "%BLENDER_USER_RESOURCES%" mkdir "%BLENDER_USER_RESOURCES%"
if not exist "%APPDATA%" mkdir "%APPDATA%"
if not exist "%BLENDER_USER_SCRIPTS%" mkdir "%BLENDER_USER_SCRIPTS%"
if not exist "%BLENDER_USER_EXTENSIONS%" mkdir "%BLENDER_USER_EXTENSIONS%"
if not exist "%BLENDER_USER_DATAFILES%" mkdir "%BLENDER_USER_DATAFILES%"
start "" "%~dp0bforartists.exe" %*
