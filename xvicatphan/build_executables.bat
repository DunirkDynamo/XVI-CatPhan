@echo off
REM Build script for CatPhan Analysis executable
REM Requires: pip install pyinstaller

echo ============================================================
echo Building CatPhan Analyzer Executable
echo ============================================================
echo.

REM Check if pyinstaller is installed
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo Error: PyInstaller not found
    echo Please install: pip install pyinstaller
    echo.
    pause
    exit /b 1
)

REM Clean previous builds
echo Cleaning previous builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
echo.

REM Build GUI Analyzer
echo Building CatPhanAnalyzer.exe...
python -m PyInstaller --clean CatPhanAnalyzer.spec
if errorlevel 1 (
    echo Error building CatPhanAnalyzer.exe
    pause
    exit /b 1
)
echo     Done: dist\CatPhanAnalyzer.exe
echo.

echo ============================================================
echo Build Complete!
echo ============================================================
echo.
echo Executable created: dist\CatPhanAnalyzer.exe
echo.
echo You can distribute this .exe file to any Windows computer.
echo No Python installation required on target machines.
echo.
pause
