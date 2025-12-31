@echo off
REM Build script for both FLL Maestro and FLL Toast

REM Derive version from git; falls back to commit hash if no tags.
for /f "usebackq tokens=* delims=" %%v in (`git describe --tags --dirty --always`) do set VERSION=%%v
if "%VERSION%"=="" set VERSION=unknown

echo Building both programs with version %VERSION%

REM Stamp version.py for unified versioning
> version.py echo __version__ = "%VERSION%"

REM Clean previous builds
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist fll-maestro.exe del fll-maestro.exe
if exist fll-toast.exe del fll-toast.exe

REM Build Maestro
pyinstaller --onefile --name fll-maestro fll-maestro.py
if exist dist\fll-maestro.exe copy /y dist\fll-maestro.exe .

REM Build Toast
pyinstaller --onefile --name fll-toast fll-toast.py
if exist dist\fll-toast.exe copy /y dist\fll-toast.exe .

echo Build complete. Version %VERSION% burned into both exes.
