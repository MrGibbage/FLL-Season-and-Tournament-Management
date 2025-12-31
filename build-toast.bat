@echo off
setlocal

rem Derive version from git; falls back to commit hash if no tags.
for /f "usebackq tokens=* delims=" %%v in (`git describe --tags --dirty --always`) do set TOAST_VERSION=%%v
if "%TOAST_VERSION%"=="" set TOAST_VERSION=unknown

echo Building TOAST version %TOAST_VERSION%

rem Activate virtual environment if needed (uncomment and adjust)
rem call .venv\Scripts\activate

rem Build using existing spec file
pyinstaller fll-toast.spec

rem Copy freshly built exe to repo root (next to fll-maestro.py)
if exist dist\fll-toast.exe (
	copy /Y dist\fll-toast.exe fll-toast.exe >nul
	echo Copied dist\fll-toast.exe to root fll-toast.exe
) else (
	echo WARNING: dist\fll-toast.exe not found; copy skipped
)

endlocal
