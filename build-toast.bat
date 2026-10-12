@echo off
REM Build script for FLL Toast (PyInstaller)

REM Clean previous build
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist fll-toast-win.exe del fll-toast-win.exe

REM Build with PyInstaller
pyinstaller --noconfirm --clean fll-toast.spec

REM Copy exe to repo root
if exist dist\fll-toast-win.exe copy /y dist\fll-toast-win.exe .

echo Build complete.
