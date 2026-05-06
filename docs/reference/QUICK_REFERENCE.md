# Quick Reference Guide

This is a compact lookup for commands, options, and APIs once you are already
familiar with the basics. If you are installing or running the tool for the
first time, start with [QUICKSTART.md](../../QUICKSTART.md).

**Version 1.0 - Working Release**

This package reproduces the analysis from processDICOMcat2.py in an object-oriented architecture.

## Installation

```bash
pip install .
```

## Quick Start

### 1. GUI Folder Selection (Easiest)

```bash
catphan-select
# Or: python -m catphan_analysis.select_and_analyze
```

### 2. Analyze CatPhan Images (Simple)

```python
from catphan_analysis import CatPhanAnalyzer

analyzer = CatPhanAnalyzer('/path/to/dicom/files')
analyzer.open_log()
analyzer.analyze()
analyzer.generate_report()
analyzer.close_log()
```

### 3. Command Line

```bash
catphan-analyze /path/to/dicom/files
# Or: catphan-analyze /path/to/dicom/files
```

### 4. Automated DICOM Monitoring

```bash
catphan-listen /path/to/receiver
# Or: python -m catphan_analysis.listen_and_analyze /path/to/receiver
```

## Class Quick Reference

### CatPhanAnalyzer (Executive Class)
```python
from catphan_analysis import CatPhanAnalyzer

analyzer = CatPhanAnalyzer(
    dicom_path='/path/to/dicom',
    output_path='/path/to/output',  # optional
    catphan_model='500'              # or '504'
)

# Recommended usage: `analyzer.analyze()` performs loading, module location,
# center finding, rotation detection (via CTP404Analyzer), and module
# initialization as needed.
analyzer.open_log()
results = analyzer.analyze()
analyzer.generate_report()
analyzer.close_log()
```

### Utility Classes

#### CatPhanGeometry
```python
from catphan_analysis.utils.geometry import CatPhanGeometry

# Find phantom center
center, boundary = CatPhanGeometry.find_center(image)

# Rotation detection is provided by the Alexandria utility or the CTP404 analyzer.
# Use one of the following:
# - `analyzer.run_ctp404()` or `analyzer.analyze()` (recommended)
# - `CTP404Analyzer.detect_rotation()` (module-level)
# - `from alexandria.utils import find_rotation` and call `find_rotation(image, center, pixel_spacing, ...)`

# Find CTP528 slice
slice_idx = CatPhanGeometry.find_slice_ctp528(dicom_set)
```

#### SliceLocator
```python
from catphan_analysis.utils.geometry import SliceLocator

locator = SliceLocator(dicom_set)
indices = locator.locate_all_modules()
# Returns: {'ctp528': idx1, 'ctp404': idx2, 'ctp486': idx3}
```

#### ImageProcessor
```python
from catphan_analysis.utils.image_processing import ImageProcessor

# Create circular mask
mask = ImageProcessor.create_circular_mask(h, w, center, radius)

# Extract line profile
profile = ImageProcessor.extract_profile(image, start, end)

# Average slices
avg_image = ImageProcessor.average_slices(dicom_set, [idx1, idx2, idx3])

# Calculate ROI stats
stats = ImageProcessor.calculate_roi_statistics(image, mask)
```

### DICOM Listener
```python
from catphan_analysis import DICOMListener

listener = DICOMListener(
    base_path='/path/to/receiver',
    sleep_interval=5,
    wait_cycles=8
)

# Set callback for when files are ready
def analyze_callback(data_path):
    analyzer = CatPhanAnalyzer(data_path)
    analyzer.analyze()
    analyzer.generate_report()

listener.set_analysis_callback(analyze_callback)
listener.start()  # Blocks until stopped with Ctrl+C
```

## Common Workflows

### Workflow 1: Standard Analysis
```python
analyzer = CatPhanAnalyzer('/path/to/dicom')
analyzer.open_log()
results = analyzer.analyze()
analyzer.generate_report()
analyzer.close_log()
```

### Workflow 2: Custom Processing
```python
analyzer = CatPhanAnalyzer('/path/to/dicom')
# If you need to perform custom preprocessing, call `load_dicom_files()` first,
# then run your preprocessing and finally call `analyzer.analyze()` which will
# complete module location, center/rotation detection, and initialization.
analyzer.load_dicom_files()
# ... custom preprocessing here ...
results = analyzer.analyze()

# Access and use individual modules (created by the analyzer)
contrast = analyzer.ctp404.analyze_contrast()
uniformity = analyzer.ctp486.analyze_uniformity()
mtf = analyzer.ctp528.analyze()

# Generate report
analyzer.generate_report()
```

### Workflow 3: Individual Module
```python
# Run full analysis, then access individual module analyzers
analyzer = CatPhanAnalyzer('/path/to/dicom')
analyzer.analyze()

# Module analyzers are Alexandria classes accessible via the executive class
results = analyzer.ctp404.analyze()
```

### Workflow 4: Batch Processing
```python
datasets = ['/path/1', '/path/2', '/path/3']

for path in datasets:
    analyzer = CatPhanAnalyzer(path)
    analyzer.analyze()
    analyzer.generate_report()
```

## Command-Line Options

### catphan-analyze
```bash
catphan-analyze <dicom_path> [OPTIONS]

Options:
  --output, -o PATH     Output directory
  --model, -m MODEL     CatPhan model (500 or 504)
  --no-plots           Skip plot generation
```

### catphan-listen
```bash
catphan-listen <base_path> [OPTIONS]

Options:
  --interval, -i SECONDS    Check interval (default: 5)
  --wait-cycles, -w COUNT   Wait cycles before processing (default: 8)
```

## Results Access

```python
# After running analyzer.analyze()
results = analyzer.results

# CTP404 results
ctp404_results = results['ctp404']
contrast_rois = ctp404_results['contrast_rois']
lcv = ctp404_results['low_contrast_visibility']
x_scale = ctp404_results['x_scale_cm']
thickness = ctp404_results['slice_thickness_mm']

# CTP486 results
ctp486_results = results['ctp486']
regions = ctp486_results['regions']
uniformity = ctp486_results['uniformity_percent']

# CTP528 results
ctp528_results = results['ctp528']
mtf_10 = ctp528_results['mtf_10']
mtf_50 = ctp528_results['mtf_50']

# Metadata
metadata = results['metadata']
unit = metadata['unit']
date = metadata['study_date']
```

## Tips

1. **Always open/close log** when using CatPhanAnalyzer
   ```python
   analyzer.open_log()
   # ... analysis ...
   analyzer.close_log()
   ```

2. **Check data loaded** before analysis
   ```python
   if analyzer.load_dicom_files() == 0:
       print("No DICOM files found!")
   ```

3. **Access intermediate results**
   ```python
   analyzer.locate_modules()
   print(f"Found CTP528 at slice {analyzer.slice_indices['ctp528']}")
   ```

4. **Use individual modules** for specific tests
   ```python
   # Only need contrast analysis?
   ctp404 = CTP404Module(...)
   contrast_results = ctp404.analyze_contrast()
   ```

5. **Batch processing** with error handling
   ```python
   for path in datasets:
       try:
           analyzer = CatPhanAnalyzer(path)
           analyzer.analyze()
       except Exception as e:
           print(f"Error with {path}: {e}")
   ```
