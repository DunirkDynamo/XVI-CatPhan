# Installation Guide

This guide covers all installation methods for the CatPhan Analysis Package.

---

## Choose Your Installation Method

| Method | Best For | Requirements | Difficulty |
|--------|----------|--------------|------------|
| **Standalone Executable** | Clinical users, non-programmers | None | ⭐ Easy |
| **Pip Package** | Python users, automation | Python 3.7+ | ⭐⭐ Moderate |
| **Development Install** | Developers, contributors | Python 3.7+, Git | ⭐⭐⭐ Advanced |

---

## Method 1: Standalone Executable (Recommended for Most Users)

### What You Get
- Single `.exe` file that runs on any Windows computer
- No Python installation required
- No dependencies to manage
- Double-click to run

### Installation Steps

1. **Download the executable:**
   - Get `CatPhanAnalyzer.exe` from the releases page or build directory
   - File size: ~50-100 MB

2. **Place it somewhere convenient:**
   ```
   Option A: Desktop (easiest)
   Option B: C:\Programs\CatPhan\CatPhanAnalyzer.exe
   Option C: Network share: \\server\Medical Physics\CatPhan\CatPhanAnalyzer.exe
   ```

3. **(Optional) Create a shortcut:**
   - Right-click the `.exe` → Send to → Desktop (create shortcut)
   - Rename shortcut to "CatPhan Analyzer"

4. **Run it:**
   - Double-click `CatPhanAnalyzer.exe`
   - Folder picker opens → select DICOM folder → analysis runs
   - Results saved in the DICOM folder

### Troubleshooting

**Windows SmartScreen Warning:**
- Click "More info" → "Run anyway"
- This is normal for unsigned executables

**Antivirus Blocks Executable:**
- Add exception in antivirus software
- Or code-sign the executable (requires certificate)

**Executable Won't Start:**
- Check Windows Event Viewer for error details
- Ensure you have write permissions to the DICOM folder

---

## Method 2: Python Package Installation

### Prerequisites

- Python 3.7 or higher
- pip (included with Python)

Check your Python version:
```bash
python --version
```

### Installation Steps

#### Step 1: Install Dependencies

```bash
pip install numpy scipy matplotlib pydicom
```

Or from requirements file:
```bash
pip install -r requirements.txt
```

#### Step 2: Install the Package

**Option A: User Installation (Recommended)**
```bash
cd /path/to/xvicatphan
pip install .
```

**Option B: Development Installation (Editable)**
```bash
cd /path/to/xvicatphan
pip install -e .
```

With `-e` (editable mode), changes to the source code take effect immediately without reinstalling.

#### Step 3: Verify Installation

```bash
# Check console commands are available
catphan-select --help
catphan-analyze --help
catphan-listen --help

# Or test in Python
python -c "from catphan_analysis import CatPhanAnalyzer; print('Success!')"
```

### What Gets Installed

- **Python package:** `catphan_analysis` module for importing
- **Console commands:**
  - `catphan-select` - GUI folder picker
  - `catphan-analyze` - Command-line analysis
  - `catphan-listen` - DICOM listener service

### Troubleshooting

**Command not found: catphan-select**
- Ensure pip install location is in PATH
- Try: `python -m pip install --user -e .`
- Or run directly: `python select_and_analyze.py`

**Import errors:**
```bash
# Check installed packages
pip list | grep -E "numpy|scipy|matplotlib|pydicom"

# Reinstall dependencies
pip install --upgrade numpy scipy matplotlib pydicom
```

**Version conflicts:**
```bash
# Create virtual environment (recommended)
python -m venv catphan_env
source catphan_env/bin/activate  # Linux/Mac
catphan_env\Scripts\activate     # Windows

# Install in isolated environment
pip install -e .
```

---

## Method 3: Development Installation

### Prerequisites

- Python 3.7+
- Git
- PyInstaller (for building executables)

### Setup Steps

#### 1. Clone Repository

```bash
git clone https://github.com/yourusername/XVI-CatPhan.git
cd XVI-CatPhan/xvicatphan
```

#### 2. Create Virtual Environment (Recommended)

```bash
# Create environment
python -m venv venv

# Activate it
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

#### 3. Install in Editable Mode

```bash
pip install -e .
```

#### 4. Install Development Tools

```bash
# For building executables
pip install pyinstaller

# For documentation
pip install sphinx sphinx_rtd_theme

# For testing (if you add tests)
pip install pytest
```

#### 5. Verify Development Setup

```bash
# Run tests
python -m pytest

# Build documentation
cd docs
make html

# Build executables
python build_executables.bat  # Windows
./build_executables.sh        # Linux/Mac
```

---

## Running Without Installation

If you don't want to install the package, you can run scripts directly:

```bash
# Navigate to package directory
cd /path/to/xvicatphan

# Ensure dependencies are installed
pip install numpy scipy matplotlib pydicom

# Run scripts directly
python select_and_analyze.py           # GUI
python main.py /path/to/dicom          # Command-line
python listen_and_analyze.py /path     # Listener
```

**Note:** Console commands (`catphan-select`, etc.) won't be available without installation.

---

## Comparison Table

| Feature | Executable | Pip Install | Development |
|---------|-----------|-------------|-------------|
| Python Required | ❌ No | ✅ Yes | ✅ Yes |
| Installation Time | Instant | ~5 min | ~10 min |
| File Size | ~100 MB | ~5 MB | ~5 MB |
| Auto-updates | ❌ Manual | ✅ `pip install -U` | ✅ `git pull` |
| Code Access | ❌ No | ✅ Read-only | ✅ Full access |
| Build Executables | ❌ No | ❌ No | ✅ Yes |
| Modify Code | ❌ No | ⚠️ Requires reinstall | ✅ Immediate |

---

## Platform Support

| Platform | Executable | Python Package |
|----------|-----------|----------------|
| Windows 10/11 | ✅ Supported | ✅ Supported |
| Linux | ❌ Use Python | ✅ Supported |
| macOS | ❌ Use Python | ✅ Supported |

**Note:** Executables are platform-specific. Windows executables don't run on Linux/Mac.

---

## Upgrading

### Executable
Download new version and replace the old `.exe` file.

### Python Package
```bash
cd /path/to/xvicatphan
git pull  # If from git
pip install --upgrade .
```

### Development Install
```bash
git pull
# No reinstall needed with -e flag
```

---

## Uninstalling

### Executable
Delete the `.exe` file. No other cleanup needed.

### Python Package
```bash
pip uninstall catphan-analysis
```

### Development Install
```bash
pip uninstall catphan-analysis
rm -rf venv/  # Remove virtual environment if created
```

---

## Network Deployment

For deploying to multiple workstations:

### Option 1: Network Share (Executable)
```
1. Place CatPhanAnalyzer.exe on network share
2. Create desktop shortcuts pointing to network location
3. Users double-click shortcut to run

Example:
  Network path: \\fileserver\Medical Physics\CatPhan\CatPhanAnalyzer.exe
  Desktop shortcut target: \\fileserver\Medical Physics\CatPhan\CatPhanAnalyzer.exe
```

### Option 2: Package Server (Python)
```bash
# Set up internal PyPI server
pip install pypiserver
pypi-server -p 8080 ./packages/

# Install from internal server
pip install --index-url http://pypi-server:8080 catphan-analysis
```

---

## Getting Help

**Installation Issues:**
1. Check this guide's Troubleshooting sections
2. Verify Python version: `python --version`
3. Check pip version: `pip --version`
4. Review installation logs for errors

**Still Stuck?**
- Check `BUILD_EXECUTABLES.md` for executable building issues
- Review `HOW_TO_USE.md` for usage instructions
- Open an issue on GitHub with:
  - Installation method attempted
  - Error messages
  - Python version
  - Operating system

---

## Next Steps

After installation:
- Read [HOW_TO_USE.md](HOW_TO_USE.md) for usage instructions
- See [QUICK_REFERENCE.md](QUICK_REFERENCE.md) for API reference
- Review [README.md](README.md) for package overview
