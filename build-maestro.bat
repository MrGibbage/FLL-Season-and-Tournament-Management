@echo off
REM Build script for FLL Maestro (PyInstaller, version stamping)

REM Set version here or pass as argument
set VERSION=0.9.2

REM Write version.py
> version.py echo __version__ = "%VERSION%"

REM Clean previous build
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist fll-maestro.exe del fll-maestro.exe

REM Build with PyInstaller
pyinstaller --onefile --name fll-maestro fll-maestro.py

REM Copy exe to repo root
if exist dist\fll-maestro.exe copy /y dist\fll-maestro.exe .

echo Build complete. Version %VERSION% burned into exe.
