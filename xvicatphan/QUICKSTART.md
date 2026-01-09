# Quick Start Guide - CatPhan Analysis

## Three Ways to Use the Package

### 1. GUI Folder Selection (Recommended for Manual Analysis)

The easiest way to analyze existing DICOM data:

```bash
python select_and_analyze.py
```

**What happens:**
1. A folder selection dialog opens
2. Navigate to your folder containing DICOM files
3. Click "Select Folder"
4. Analysis runs automatically
5. Results are saved to the same folder

**Output files in the selected folder:**
- `analysis_log.txt` - Detailed analysis log
- `catphan_report.txt` - Results summary
- Various `.png` plots for each module

---

### 2. Command Line Analysis

For scripting or when you know the path:

```bash
# Basic usage
python main.py /path/to/dicom/files

# Custom output location
python main.py /path/to/dicom/files --output /path/to/results

# Specify CatPhan model (default is 500)
python main.py /path/to/dicom/files --model 504
```

---

### 3. Automated Listening (For DICOM Receivers)

For automated analysis when files arrive:

```bash
python listen_and_analyze.py /path/to/dicom/receiver
```

**What it does:**
- Monitors a folder for new DICOM files
- Waits for transfer to complete
- Automatically analyzes new data
- Saves results to analysis subfolder

**Options:**
```bash
# Check every 10 seconds (default: 5)
python listen_and_analyze.py /path/to/receiver --interval 10

# Wait 5 cycles before processing (default: 8)
python listen_and_analyze.py /path/to/receiver --wait-cycles 5
```

---

## Quick Example Workflow

### Scenario: Analyze yesterday's QA scan

1. Run the GUI selector:
   ```bash
   python select_and_analyze.py
   ```

2. Browse to your DICOM folder, e.g.:
   ```
   C:\QA_Data\2026-01-04_CatPhan\
   ```

3. Click "Select Folder"

4. Wait for analysis to complete (typically 30-60 seconds)

5. Find results in the same folder:
   ```
   C:\QA_Data\2026-01-04_CatPhan\
   ├── analysis_log.txt          <- Detailed log
   ├── catphan_report.txt        <- Summary report
   ├── ctp404_hu_plot.png        <- HU linearity
   ├── ctp404_contrast_plot.png  <- Low contrast
   ├── ctp486_uniformity_plot.png <- Uniformity
   └── ctp528_mtf_plot.png       <- Resolution
   ```

---

## Installation

If you haven't installed yet:

```bash
# Install the package
pip install -e .

# Or just install dependencies
pip install -r requirements.txt
```

After installation, you can use console commands:

```bash
catphan-select    # GUI folder selection
catphan-analyze   # Command line analysis
catphan-listen    # Automated listener
```

---

## Troubleshooting

### "No DICOM files found"
- Make sure the folder contains DICOM files (not just subfolders)
- DICOM files typically have no extension or `.dcm` extension

### "Can't import file"
- Some files may not be valid DICOM - this is normal
- Check `analysis_log.txt` for details on skipped files

### GUI doesn't appear
- Make sure you have Python with tkinter installed
- On Linux: `sudo apt-get install python3-tk`
- On macOS/Windows: tkinter is included by default

### Analysis fails
- Check that you have a complete CatPhan scan
- Typical scan has 40-80 slices
- All three modules (CTP404, CTP486, CTP528) must be present
