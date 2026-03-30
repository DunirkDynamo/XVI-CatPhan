# Building Standalone Executables

This document explains how to build standalone Windows executables for the CatPhan Analysis package.

## Overview

The package can be distributed in two ways:
1. **Python package** (`pip install`) - For developers and command-line users
2. **Standalone executables** (`.exe` files) - For clinical users who don't have Python installed

## Prerequisites

**PyInstaller is required** to build executables. This is NOT a runtime dependency - only install if you want to build executables.

```bash
pip install -e .[build]
```

This installs `pyinstaller` without making it a runtime dependency for end users.

## Building the Executable

### Option 1: Automated Build (Recommended)

**First time:** Install PyInstaller (see Prerequisites above)

Run the build script:
```bash
scripts/build_executables.bat
```

This will:
- Check if PyInstaller is installed (exits with error if not found)
- Clean previous build files
- Build `dist/CatPhanAnalyzer.exe`

### Option 2: Manual Build

Build using the spec file:

```bash
python -m PyInstaller packaging/pyinstaller/CatPhanAnalyzer.spec
```

### Option 3: Quick Build (No Spec File)

```bash
python -m PyInstaller --onefile --windowed --name=CatPhanAnalyzer src/catphan_analysis/select_and_analyze.py
```

## Versioning for Releases

Package versions are derived dynamically from Git tags using `setuptools-scm`.

Typical release flow:

```bash
git tag v1.0.1
git push origin main --tags
```

When building from a tagged commit, the package and generated metadata will use that tag-derived version automatically.

## The Executable

## File Locations

- Build script: `scripts/build_executables.bat`
- PyInstaller spec: `packaging/pyinstaller/CatPhanAnalyzer.spec`
- GUI entrypoint: `src/catphan_analysis/select_and_analyze.py`

### CatPhanAnalyzer.exe
- **Purpose:** GUI-based folder selection and analysis
- **Usage:** Double-click to run
- **Interface:** Opens folder picker dialog → Select DICOM folder → Analysis runs → Results saved
- **Console:** Hidden (GUI mode)
- **Size:** ~50-100 MB (includes Python, numpy, scipy, matplotlib, pydicom)

## Distribution

The `.exe` files are completely standalone:
- No Python installation required on target machine
- No dependencies to install
- Copy to any Windows computer and run
- Can be placed on network share for easy access

### Typical Deployment

1. Build executable on development machine
2. Copy `dist/CatPhanAnalyzer.exe` to network share or USB drive
3. On target computer:
   - Create desktop shortcut to the `.exe`
   - Double-click to use

## Adding an Icon

To customize the executable icon:

1. Create or obtain `catphan.ico` file (must be `.ico` format)
2. Place in project root
3. Update spec files:
   ```python
   icon='catphan.ico'  # Change from None
   ```
4. Rebuild executables

## Troubleshooting

### Build Fails with Import Errors

Add missing modules to `hiddenimports` in the spec file:
```python
hiddenimports=[
    'missing_module_name',
]
```

### Executable is Too Large

Current size (~50-100 MB) is normal for scientific Python applications. To reduce:
- Use `--exclude-module` for unused packages (not recommended - may break functionality)
- Consider distributing as installer instead of single file

### Executable Crashes on Startup

1. Test with console visible: Change `console=True` in spec file
2. Run from command prompt to see error messages
3. Check for missing data files or hiddenimports

### Antivirus Blocks Executable

Some antivirus software flags PyInstaller executables:
- This is a false positive
- Consider code signing certificate for distribution
- Add exception in antivirus software

## File Size Comparison

| Distribution Method | Size | Requirements |
|---------------------|------|--------------|
| Python Package | ~5 MB | Python + pip installed |
| Standalone .exe | ~50-100 MB | None |

## Notes

- Executables are Windows-only (built on Windows for Windows)
- For Linux/Mac, users should use `pip install` method
- Rebuilding required after any code changes
- Spec file preserves build configuration for reproducibility
- Build time: ~1-2 minutes

## Development Workflow

1. Develop and test using pip-installed package
2. When ready for release, build executable
3. Test executable on clean machine (no Python)
4. Distribute `.exe` file to end users
5. Keep spec file in version control
