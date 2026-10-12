@echo off
REM Build script for FLL Toast (PyInstaller)

REM Clean previous build
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist fll-toast.exe del fll-toast.exe

REM Build with PyInstaller
pyinstaller --noconfirm --clean fll-toast.spec

REM Copy exe to repo root
if exist dist\fll-toast.exe copy /y dist\fll-toast.exe .

echo Build complete.
