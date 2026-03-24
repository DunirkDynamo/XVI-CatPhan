# CatPhan Analysis Package

A professional, object-oriented software package for analyzing CatPhan phantom DICOM images. This package provides modular, class-based analysis of CTP404, CTP486, and CTP528 modules with accurate reproduction of the original analysis algorithms.

## Status

**Version 1.0 - Working Release**

This package has been validated against the original reference implementation (processDICOMcat2.py) and produces matching results for all analysis modules.

## Quick Start

**For Non-Technical Users (No Python Required):**

Download `CatPhanAnalyzer.exe` and double-click to run. A folder picker will open - select your DICOM folder and analysis runs automatically.

**For Python Users:**

```bash
pip install -e .
catphan-select  # Opens GUI folder picker
```

See [INSTALLATION.md](INSTALLATION.md) for detailed installation options.

## Features

- **Modular Architecture**: Each analysis module (CTP404, CTP486, CTP528) is implemented as a separate class
- **Executive Class**: `CatPhanAnalyzer` coordinates all analysis modules
- **GUI Folder Selection**: Easy-to-use folder browser for selecting DICOM data
- **Automated Processing**: DICOM listener for automated file reception and analysis
- **Comprehensive Analysis**:
  - CTP404: Contrast, HU accuracy, spatial scaling, slice thickness
  - CTP486: Image uniformity (5-region analysis)
  - CTP528: Spatial resolution (MTF) with line pair profile visualization
- **Validated Algorithms**: All calculations match the reference implementation

## Package Structure

```
catphan_analysis/
├── __init__.py              # Package initialization
├── analyzer.py              # Executive CatPhanAnalyzer class
├── dicom_listener.py        # DICOM file monitoring and processing
└── utils/
    ├── __init__.py
    ├── geometry.py         # Geometric calculations
    └── image_processing.py # Image processing utilities
```

## Installation

### Option 1: Standalone Executable (Recommended for Clinical Users)

No Python installation required. Download `CatPhanAnalyzer.exe` and run it.

### Option 2: Python Package Installation

```bash
# Install the package
cd /path/to/xvicatphan
pip install -e .
```

### Alexandria Development Setup (Local)

Alexandria is a local library in this repo and is not yet published to PyPI. For
development, install it in editable mode before running this project:

```bash
cd /path/to/xvicatphan
python -m venv .venv
./.venv/bin/activate  # On Windows: .\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e ../../alexandria
pip install -e .
```

**See [INSTALLATION.md](INSTALLATION.md) for complete installation instructions and troubleshooting.**

## Usage

### Basic Analysis

Analyze a directory of CatPhan DICOM files:

```python
from catphan_analysis import CatPhanAnalyzer

# Create analyzer
analyzer = CatPhanAnalyzer(
    dicom_path='/path/to/dicom/files',
    output_path='/path/to/output'
)

# Run analysis
analyzer.open_log()
results = analyzer.analyze()
analyzer.generate_report()
analyzer.close_log()
```

### Command Line

```bash
# Basic usage
# Basic usage
catphan-analyze /path/to/dicom/files

# With output directory
# With output directory
catphan-analyze /path/to/dicom/files --output /path/to/output

# Specify CatPhan model
# Specify CatPhan model
catphan-analyze /path/to/dicom/files --model 504
```

### GUI Folder Selection

Use the graphical folder browser to select data for analysis:

```bash
python -m catphan_analysis.select_and_analyze
```

This opens a folder selection dialog. Navigate to a folder containing DICOM files, and the analysis will run automatically with results saved to that same folder.

### Automated DICOM Listening

Run a service that monitors for incoming DICOM files:

```bash
python -m catphan_analysis.listen_and_analyze /path/to/dicom/receiver
```

### Using Individual Modules

```python
from alexandria import CTP404Analyzer, UniformityAnalyzer, HighContrastAnalyzer

# Initialize a module
ctp404 = CTP404Analyzer(
    dicom_set=dicom_datasets,
    slice_index=50,
    center=(256, 256),
    rotation_offset=0.0
)

# Run analysis
results = ctp404.analyze()
```

## Class Architecture

### Executive Class: CatPhanAnalyzer

The main class that coordinates the entire analysis workflow:

```python
class CatPhanAnalyzer:
    def __init__(self, dicom_path, output_path, catphan_model)
    def load_dicom_files()
    def locate_modules()
    def find_module_centers()
    # rotation detection is handled by the CTP404 analyzer (see `run_ctp404()`)
    def initialize_modules()
    def analyze()
    def generate_report()
```

### Analysis Module Classes

The analysis modules are provided by the Alexandria library:

#### CTP404Analyzer - Contrast and Spatial Linearity
- Measures HU values for different materials
- Calculates low contrast visibility
- Verifies spatial scaling
- Measures slice thickness

#### UniformityAnalyzer - Uniformity
- Measures uniformity across 5 regions
- Calculates uniformity percentage

#### HighContrastAnalyzer - Spatial Resolution
- Analyzes line pair patterns
- Calculates Modulation Transfer Function (MTF)
- Reports MTF at 10%, 30%, 50%, 80%

### Utility Classes

- **CatPhanGeometry**: Geometric calculations (center finding). Rotation detection now delegates
    to the centralized Alexandria utility (`alexandria.utils.find_rotation`) to avoid duplicated
    implementations across projects. Use `CatPhanAnalyzer` (see below) which will prefer
    the `CTP404Analyzer.detect_rotation()` implementation when running full analysis.
- **SliceLocator**: Locates phantom modules in DICOM series
- **ImageProcessor**: Image processing operations

## Migration from Legacy Code

This package refactors the original procedural scripts:
- `analyzeDICOM_Catphan.py` → `dicom_listener.py`
- `processDICOMcat.py` → Distributed across module classes

### Key Improvements

1. **Object-Oriented Design**: Functions converted to classes with clear responsibilities
2. **Modular Structure**: Each analysis module is independent
3. **Reusability**: Classes can be used individually or together
4. **Maintainability**: Clear separation of concerns
5. **Extensibility**: Easy to add new modules or features

## Example: Custom Analysis Workflow

```python
from catphan_analysis import CatPhanAnalyzer

# Create analyzer with custom settings
analyzer = CatPhanAnalyzer(
    dicom_path='C:/Data/CatPhan',
    catphan_model='500'
)

# Load and prepare data
    analyzer.load_dicom_files()
    analyzer.locate_modules()
    analyzer.find_module_centers()

    # Detect rotation and run the CTP404 module (this will set rotation and
    # refine the CTP404 center). You can run the full analysis with
    # `analyzer.analyze()` instead.
    analyzer.run_ctp404()

    # Initialize specific modules (if you prefer manual control)
    analyzer.initialize_modules()

# Access individual modules
ctp404 = analyzer.ctp404
ctp486 = analyzer.ctp486
ctp528 = analyzer.ctp528

# Run custom analysis on specific module
contrast_results = ctp404.analyze_contrast()
lcv = ctp404.calculate_low_contrast_visibility()

# Generate full report
analyzer.analyze()
analyzer.generate_report()
```

## Documentation

Full documentation is available and built with Sphinx:

### Building Documentation

```bash
cd docs
make html  # Unix/Mac
# or
make.bat html  # Windows
```

Then open `docs/_build/html/index.html` in your browser.

### Documentation Includes

- Installation guide
- Quick start tutorial
- Detailed user guide
- Complete API reference (auto-generated from docstrings)
- Usage examples

See [SPHINX_GUIDE.md](SPHINX_GUIDE.md) for detailed documentation building instructions.

## Requirements

- Python 3.7+
- numpy
- scipy
- matplotlib
- pydicom
- sphinx (for building documentation)
- sphinx-rtd-theme (for documentation theme)

## License

[Your License Here]

## Authors

Refactored from original procedural scripts to object-oriented package.

## Notes

- Supports CatPhan 500 and 504 models
- Designed for automated QA workflows
- Compatible with network DICOM receivers
