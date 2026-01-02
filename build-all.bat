@echo off
setlocal enabledelayedexpansion
REM Build script for both FLL Maestro and FLL Toast


echo --- Step: Extracting commit_message from version.py ---
echo Commit message from version.py: %COMMIT_MSG%
echo Version from version.py: %VERSION_STR%

echo --- Diagnostic: Displaying contents of version.json ---
type version.json

echo --- Step: Extracting commit_message and version from version.json ---
for /f "delims=" %%a in ('powershell -Command "(Get-Content version.json | ConvertFrom-Json).commit_message"') do set "COMMIT_MSG=%%a"
for /f "delims=" %%a in ('powershell -Command "(Get-Content version.json | ConvertFrom-Json).version"') do set "VERSION_STR=%%a"
echo Commit message from version.json: %COMMIT_MSG%
echo Version from version.json: %VERSION_STR%

REM Stop if commit_message is missing
if "%COMMIT_MSG%"=="" (
    echo ERROR: commit_message is missing in version.json. Aborting build.
    exit /b 1
)


echo --- Step: Git add, show staged files, and prompt for commit ---
git add .
REM Check for staged changes before committing
git diff --cached --quiet
if %errorlevel%==0 (
    echo No changes to commit. Skipping git commit.
) else (
    echo.
    echo Staged files for commit:
    git diff --cached --name-only
    echo.
    echo Commit message to use:
    echo ----------------------
    echo %COMMIT_MSG%
    echo ----------------------
    echo.
    set /p USER_CHOICE="Proceed with this commit message? (Y = yes, E = edit message, Q = quit build) [Y/E/Q]: "
    if /I "!USER_CHOICE!"=="Q" (
        echo Aborting build by user request.
        exit /b 1
    )
    if /I "!USER_CHOICE!"=="E" (
        set /p COMMIT_MSG="Enter new commit message: "
    )
    echo About to run: git commit -m "%COMMIT_MSG%"
    git commit -m "%COMMIT_MSG%"
    if errorlevel 1 (
        echo ERROR: git commit failed. Aborting build.
        exit /b 1
    )
    git push
    echo Git commit and push complete.
)


REM (No longer stamping version.py or updating commit_message)

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
