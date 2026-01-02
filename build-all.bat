@echo off
setlocal enabledelayedexpansion
REM Build script for both FLL Maestro and FLL Toast

echo --- Step: Extracting commit_message from version.py ---
set "COMMIT_MSG="
for /f "tokens=2* delims== " %%a in ('findstr commit_message version.py') do set "COMMIT_MSG=%%a"
echo Raw COMMIT_MSG=%COMMIT_MSG%

REM Remove all quotes from COMMIT_MSG
set "COMMIT_MSG=%COMMIT_MSG:"=%"
echo Final COMMIT_MSG=%COMMIT_MSG%

REM Stop if commit_message is missing
if "%COMMIT_MSG%"=="" (
    echo ERROR: commit_message is missing in version.py. Aborting build.
    exit /b 1
)

echo --- Step: Stamping version.py ---
echo __version__ = "pending" > version.py
echo commit_message = "%COMMIT_MSG%" >> version.py

echo --- Step: Git add, commit, and push ---
git add .
REM Check for staged changes before committing
git diff --cached --quiet
if %errorlevel%==0 (
    echo No changes to commit. Skipping git commit.
) else (
    echo About to run: git commit -m "%COMMIT_MSG%"
    git commit -m "%COMMIT_MSG%"
    if errorlevel 1 (
        echo ERROR: git commit failed. Aborting build.
        exit /b 1
    )

    git push
    echo Git commit and push complete.
)

echo --- Step: Deriving version from git (after commit) ---
for /f "usebackq tokens=* delims=" %%v in (`git describe --tags --dirty --always`) do set VERSION=%%v
echo VERSION=%VERSION%

REM Now stamp version.py with the clean version
echo __version__ = "%VERSION%" > version.py
echo commit_message = "%COMMIT_MSG%" >> version.py

git add version.py
git commit -m "Update version.py with clean version %VERSION%" >nul 2>&1
if errorlevel 1 (
    echo No changes to commit for version.py.
) else (
    git push
    echo Git commit and push for version.py complete.
)

echo --- Step: Building both programs with version %VERSION% ---

REM Clean previous builds
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
endlocal
