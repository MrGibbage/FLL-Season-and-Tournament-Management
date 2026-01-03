@echo off
setlocal


rem Derive version from git; falls back to commit hash if no tags.
for /f "usebackq tokens=* delims=" %%v in (`git describe --tags --dirty --always`) do set TOAST_VERSION=%%v
if "%TOAST_VERSION%"=="" set TOAST_VERSION=unknown


rem call .venv\Scripts\activate

rem Build using existing spec file
pyinstaller fll-toast.spec

:: Build Toast EXE
pyinstaller --clean --onefile --name fll-toast fll-toast.py
if exist dist\fll-toast.exe (
	copy /Y dist\fll-toast.exe fll-toast.exe >nul
	echo Copied dist\fll-toast.exe to root fll-toast.exe
) else (
	echo WARNING: dist\fll-toast.exe not found; copy skipped
)

endlocal
