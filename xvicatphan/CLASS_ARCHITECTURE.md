# CatPhan Analysis - Class Architecture

**Version 1.0 - Working Release**

This document describes the object-oriented architecture that replaces the procedural processDICOMcat2.py implementation while maintaining numerical accuracy.

## Design Principles

1. **Separation of Concerns**: Each module (CTP404, CTP486, CTP528) is independent
2. **Architectural Purity**: Modules don't know how to locate themselves (SliceLocator handles this)
3. **Algorithm Fidelity**: All calculations match the reference implementation
4. **Reusability**: Classes can be used independently or orchestrated by CatPhanAnalyzer

## Class Hierarchy Overview

```
catphan_analysis/
│
├── CatPhanAnalyzer (Executive Class)
│   ├── Uses: CTP404Module
│   ├── Uses: CTP486Module
│   ├── Uses: CTP528Module
│   ├── Uses: SliceLocator
│   ├── Uses: CatPhanGeometry
│   └── Uses: ImageProcessor
│
├── Analysis Modules
│   ├── CTP404Module (Contrast/Linearity)
│   ├── CTP486Module (Uniformity)
│   └── CTP528Module (Resolution)
│
├── Utility Classes
│   ├── CatPhanGeometry (Geometric calculations)
│   ├── SliceLocator (Module location)
│   └── ImageProcessor (Image operations)
│
└── DICOM Processing
    ├── DICOMListener (File monitoring)
    └── DICOMProcessor (Automated analysis)
```

## Class Relationships

```
┌─────────────────────────────────────────────────────────────┐
│                     CatPhanAnalyzer                         │
│  (Executive class - coordinates entire workflow)            │
│                                                              │
│  + __init__(dicom_path, output_path, catphan_model)        │
│  + load_dicom_files() → int                                │
│  + locate_modules() → dict                                 │
│  + find_module_centers() → dict                            │
│  + find_rotation() → float                                 │
│  + initialize_modules()                                     │
│  + analyze() → dict                                        │
│  + generate_report() → Path                                │
│                                                              │
│  - dicom_set: list                                         │
│  - ctp404: CTP404Module                                    │
│  - ctp486: CTP486Module                                    │
│  - ctp528: CTP528Module                                    │
└─────────────────────────────────────────────────────────────┘
                    │
                    │ creates/uses
                    ▼
    ┌───────────────────────────────────────────┐
    │                                           │
    ▼                       ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│CTP404Module  │    │CTP486Module  │    │CTP528Module  │
│              │    │              │    │              │
│+ analyze()   │    │+ analyze()   │    │+ analyze()   │
│+ analyze_    │    │+ analyze_    │    │+ select_     │
│  contrast()  │    │  uniformity()│    │  optimal_    │
│+ calculate_  │    │              │    │  slices()    │
│  lcv()       │    │              │    │              │
└──────────────┘    └──────────────┘    └──────────────┘


Utility Classes (Used by all modules):

┌────────────────────┐    ┌────────────────────┐
│ CatPhanGeometry    │    │ ImageProcessor     │
│                    │    │                    │
│+ find_center()     │    │+ create_circular_  │
│+ find_rotation()   │    │  mask()            │
│+ find_slice_       │    │+ extract_profile() │
│  ctp528()          │    │+ average_slices()  │
└────────────────────┘    └────────────────────┘

┌────────────────────┐
│ SliceLocator       │
│                    │
│+ locate_all_       │
│  modules()         │
└────────────────────┘


DICOM Processing (Separate workflow):

┌────────────────────┐    ┌────────────────────┐
│ DICOMListener      │───▶│ DICOMProcessor     │
│                    │    │                    │
│+ start()           │    │+ check_and_       │
│+ stop()            │    │  process()         │
│+ set_analysis_     │    │                    │
│  callback()        │    │                    │
└────────────────────┘    └────────────────────┘
```

## Detailed Class Specifications

### 1. CatPhanAnalyzer (Executive)

**Purpose:** Coordinates the entire analysis workflow

**Attributes:**
```python
dicom_path: Path                    # Input directory
output_path: Path                   # Output directory
catphan_model: str                  # Model ('500' or '504')
dicom_set: List[pydicom.Dataset]   # Loaded DICOM files
slice_indices: dict                 # Module slice locations
module_centers: dict                # Module centers
rotation_offset: float              # Phantom rotation
ctp404: CTP404Module               # Contrast module instance
ctp486: CTP486Module               # Uniformity module instance
ctp528: CTP528Module               # Resolution module instance
results: dict                       # Analysis results
log_file: Path                      # Log file path
```

**Key Methods:**
```python
load_dicom_files() → int
    # Load and sort DICOM files by slice location
    # Returns: Number of files loaded

locate_modules() → dict
    # Find slice indices for all three modules
    # Returns: {'ctp528': idx, 'ctp404': idx, 'ctp486': idx}

find_module_centers() → dict
    # Find center of each module
    # Returns: {'ctp528': (x,y), 'ctp404': (x,y), 'ctp486': (x,y)}

find_rotation() → float
    # Determine phantom rotation angle
    # Returns: Rotation in degrees

initialize_modules()
    # Create instances of all three module classes

analyze() → dict
    # Run complete analysis on all modules
    # Returns: Complete results dictionary

generate_report(include_plots=True) → Path
    # Generate text report and plots
    # Returns: Path to report file
```

### 2. CTP404Module (Contrast/Linearity)

**Purpose:** Analyze contrast, HU accuracy, and spatial scaling

**Attributes:**
```python
dicom_set: List[Dataset]    # DICOM data
slice_index: int            # Slice location
center: Tuple[float, float] # Module center
rotation_offset: float      # Rotation angle
averaged_image: ndarray     # 3-slice average
results: list               # ROI measurements
roi_coordinates: list       # ROI positions
scaling_results: dict       # X/Y scaling
slice_thickness: float      # Measured thickness
```

**Constants:**
```python
MATERIALS = [
    'Delrin', 'none', 'Acrylic', 'Air',
    'Polystyrene', 'LDPE', 'PMP', 'Teflon', 'Air2'
]
ROI_ANGLES = [0, 30, 60, 90, 120, 180, -120, -60, -90]
```

**Key Methods:**
```python
prepare_image() → ndarray
    # Create 3-slice averaged image

analyze_contrast() → list
    # Measure HU for all material ROIs
    # Returns: [[roi_num, material, mean, std], ...]

calculate_low_contrast_visibility() → float
    # Calculate LCV metric
    # Returns: LCV value

calculate_spatial_scaling() → Tuple[float, float, list]
    # Verify X and Y scaling
    # Returns: (x_scale_cm, y_scale_cm, points)

measure_slice_thickness() → float
    # Measure slice thickness from wire ramp
    # Returns: Thickness in mm

analyze() → dict
    # Complete analysis
    # Returns: {contrast_rois, lcv, scales, thickness}
```

### 3. CTP486Module (Uniformity)

**Purpose:** Analyze image uniformity

**Attributes:**
```python
dicom_set: List[Dataset]    # DICOM data
slice_index: int            # Slice location
center: Tuple[float, float] # Module center
roi_box_size: float         # ROI size in mm
roi_offset: float           # ROI offset in mm
averaged_image: ndarray     # 3-slice average
results: list               # Region measurements
roi_coordinates: list       # ROI positions
uniformity_percent: float   # Uniformity value
```

**Constants:**
```python
REGIONS = ['centre', 'north', 'south', 'east', 'west']
```

**Key Methods:**
```python
prepare_image() → ndarray
    # Create 3-slice averaged image

analyze_uniformity() → Tuple[list, ndarray, list]
    # Measure uniformity in 5 regions
    # Returns: (results, composite_mask, roi_coords)

analyze() → dict
    # Complete analysis
    # Returns: {regions, uniformity_percent, roi_coordinates}
```

### 4. CTP528Module (Resolution)

**Purpose:** Analyze spatial resolution (MTF)

**Attributes:**
```python
dicom_set: List[Dataset]    # DICOM data
slice_index: int            # Slice location
center: Tuple[float, float] # Module center
rotation_offset: float      # Rotation angle
averaged_image: ndarray     # Multi-slice average
mtf: ndarray               # MTF values
lp_frequencies: ndarray     # Line pair frequencies
results: dict               # MTF results
```

**Key Methods:**
```python
select_optimal_slices(search_range=2) → Tuple[ndarray, list, float]
    # Choose best slices for averaging
    # Returns: (averaged_image, means, z_offset)

analyze() → dict
    # Complete MTF analysis
    # Returns: {mtf_10, mtf_30, mtf_50, mtf_80, arrays}

_calculate_mtf() → Tuple
    # Internal MTF calculation
```

### 5. CatPhanGeometry (Utility)

**Purpose:** Geometric calculations

**All methods are static:**
```python
@staticmethod
find_center(image, threshold=400) → Tuple[list, list]
    # Find phantom center from image
    # Returns: (center_coords, boundary_coords)

@staticmethod
find_rotation(image, center, search_radius=58.5) → Tuple[float, tuple, tuple]
    # Find rotation angle
    # Returns: (angle_degrees, top_point, bottom_point)

@staticmethod
find_slice_ctp528(dicom_set, expected_slice=86) → int
    # Locate CTP528 slice
    # Returns: Slice index

@staticmethod
calculate_slice_thickness(image, pixel_spacing, center) → float
    # Calculate slice thickness
    # Returns: Thickness in mm
```

### 6. SliceLocator (Utility)

**Purpose:** Locate all modules in DICOM series

**Attributes:**
```python
dicom_set: List[Dataset]    # DICOM data
ctp528_index: int           # CTP528 location
ctp404_index: int           # CTP404 location
ctp486_index: int           # CTP486 location
```

**Key Methods:**
```python
locate_all_modules() → dict
    # Find all three modules
    # Returns: {ctp528, ctp404, ctp486}
```

### 7. ImageProcessor (Utility)

**Purpose:** Image processing operations

**All methods are static:**
```python
@staticmethod
create_circular_mask(h, w, center, radius) → ndarray
    # Create circular ROI mask

@staticmethod
extract_profile(image, start, end, num_points=100) → ndarray
    # Extract intensity profile along line

@staticmethod
average_slices(dicom_set, indices) → ndarray
    # Average multiple slices

@staticmethod
apply_window_level(image, window, level) → ndarray
    # Apply display windowing

@staticmethod
calculate_roi_statistics(image, mask) → dict
    # Calculate ROI statistics
```

### 8. DICOMListener (DICOM Processing)

**Purpose:** Monitor directory for incoming DICOM files

**Attributes:**
```python
base_path: Path             # Base directory
new_data_path: Path         # Incoming files
qa_path: Path               # QA destination
other_path: Path            # Non-QA destination
analysis_path: Path         # Analysis flags
sleep_interval: int         # Check interval
wait_cycles: int            # Cycles before processing
is_running: bool            # Running state
analysis_callback: Callable # Custom callback
```

**Key Methods:**
```python
start()
    # Begin monitoring (blocking)

stop()
    # Stop monitoring

set_analysis_callback(callback)
    # Set callback for processing
```

### 9. DICOMProcessor (DICOM Processing)

**Purpose:** Process flagged analyses

**Attributes:**
```python
analyzer_class: Type        # Analyzer class to use
analysis_dir: Path          # Flag directory
```

**Key Methods:**
```python
check_and_process() → int
    # Process pending analyses
    # Returns: Number processed
```

## Data Flow

```
Input DICOM Files
      │
      ▼
CatPhanAnalyzer.load_dicom_files()
      │
      ▼
SliceLocator.locate_all_modules()
      │
      ▼
CatPhanGeometry.find_center() × 3
      │
      ▼
CatPhanGeometry.find_rotation()
      │
      ▼
CatPhanAnalyzer.initialize_modules()
      │
      ├──▶ CTP404Module.analyze()
      │         ├─ prepare_image()
      │         ├─ analyze_contrast()
      │         ├─ calculate_lcv()
      │         ├─ calculate_spatial_scaling()
      │         └─ measure_slice_thickness()
      │
      ├──▶ CTP486Module.analyze()
      │         ├─ prepare_image()
      │         └─ analyze_uniformity()
      │
      └──▶ CTP528Module.analyze()
                ├─ select_optimal_slices()
                └─ _calculate_mtf()
      │
      ▼
Results Dictionary
      │
      ▼
CatPhanAnalyzer.generate_report()
      │
      ▼
Output Files (text + plots)
```

## Design Patterns Used

1. **Facade Pattern**: CatPhanAnalyzer provides simplified interface to complex subsystem
2. **Strategy Pattern**: Different analysis strategies for each module
3. **Observer Pattern**: DICOMListener callbacks for event handling
4. **Singleton (implicit)**: Utility classes with static methods
5. **Template Method**: Module classes follow common analysis template

## Extension Points

1. **Add New Module**: Create class inheriting common structure
2. **Custom Analyzer**: Subclass CatPhanAnalyzer
3. **Custom Utilities**: Add to utils package
4. **Processing Callbacks**: DICOMListener callbacks
5. **Custom Reports**: Override generate_report()
