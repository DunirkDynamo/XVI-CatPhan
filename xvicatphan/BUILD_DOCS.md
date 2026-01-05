# Quick Start: Building Documentation

## Prerequisites

Install Sphinx:

```bash
pip install sphinx sphinx-rtd-theme
```

Or install all dependencies:

```bash
pip install -r requirements.txt
```

## Build Documentation (3 Steps)

### Step 1: Navigate to docs directory

```bash
cd docs
```

### Step 2: Build HTML documentation

**Windows:**
```bash
make.bat html
```

**Unix/Mac/Linux:**
```bash
make html
```

### Step 3: Open the documentation

**Windows:**
```bash
start _build\html\index.html
```

**Mac:**
```bash
open _build/html/index.html
```

**Linux:**
```bash
xdg-open _build/html/index.html
```

## That's It!

Your documentation is now built and includes:

- Installation guide
- Quick start tutorial  
- User guide
- **Complete API reference auto-generated from your docstrings**
- 8+ comprehensive examples

## Common Commands

```bash
# Clean and rebuild
cd docs
make clean && make html

# Check for broken links
cd docs
make linkcheck

# Build PDF (requires LaTeX)
cd docs
make latexpdf
```

## Host on Read the Docs

1. Push code to GitHub
2. Go to https://readthedocs.org
3. Click "Import a Project"
4. Select your repository
5. Done! Docs build automatically on every commit

The `.readthedocs.yml` file is already configured.

## What Gets Documented

Sphinx automatically extracts documentation from:

- All class docstrings
- All method docstrings
- Module-level docstrings
- Function docstrings

Example from your code:

```python
class CatPhanAnalyzer:
    """
    Executive class for coordinating CatPhan phantom analysis.
    
    This class initializes and manages all analysis module classes,
    coordinates the analysis workflow, and generates reports.
    """
```

This becomes beautiful HTML documentation automatically!

## Need Help?

See [SPHINX_GUIDE.md](SPHINX_GUIDE.md) for detailed instructions.
