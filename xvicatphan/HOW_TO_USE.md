# How to Use CatPhan Analysis Package

This guide explains the different ways you can use this package to analyze CatPhan phantom images.

## Choosing Your Method

**No Python? Use the Executable** - Download `CatPhanAnalyzer.exe`, double-click, and go.

**Have Python? Multiple Options** - GUI, command-line, or automated listener.

See [INSTALLATION.md](INSTALLATION.md) for installation details.

---

## Installation

**Important:** Install the package properly to avoid naming conflicts and get convenient command-line tools.

```bash
# Option 1: Install in development mode (recommended for testing)
cd /path/to/xvicatphan
pip install -e .

# Option 2: Install from requirements only (manual script execution)
pip install -r requirements.txt
```

**Why install the package?**
- Creates unique command-line tools: `catphan-analyze`, `catphan-select`, `catphan-listen`
- No conflicts with other installed packages
- Can run from any directory
- Easier to use in production

**Without installation**, you must run scripts directly from the package directory:
```bash
cd /path/to/xvicatphan
python select_and_analyze.py
```

---

## Using the Package

### Method 0: Standalone Executable (No Python Required)

**Best for:** Clinical users without Python installed

**Requirements:** None - completely standalone

**How to use:**

1. Download `CatPhanAnalyzer.exe` from releases or build directory
2. (Optional) Create a desktop shortcut or copy to preferred location
3. Double-click `CatPhanAnalyzer.exe`
4. A folder browser window will appear
5. Navigate to the folder containing your CatPhan DICOM files
6. Click "Select Folder"
7. Analysis runs automatically
8. Results are saved in the same folder:
   - `CatPhan_results.png` - Visualization plots
   - `CatPhan_results.txt` - Text report
   - `ScriptLog.txt` - Processing log

**When to use this:**
- You don't have Python installed
- You want the simplest possible setup
- You prefer a standalone application
- You're distributing to clinical staff

**Note:** The executable is ~50-100 MB but requires no additional setup.

---

## Three Ways to Use (Python Package)

### 1. GUI Folder Selection (Easiest for One-Time Analysis)

**Best for:** Analyzing a single dataset with a simple click interface

**How to use:**

**If package is installed:**
```bash
catphan-select
```

**If running without installation:**
```bash
cd /path/to/xvicatphan
python select_and_analyze.py
```

1. A folder browser window will appear
3. Navigate to the folder containing your CatPhan DICOM files
4. Click "Select Folder"
5. The analysis runs automatically
6. Results are saved in the same folder:
   - `CatPhan_results.png` - Visualization plots
   - `CatPhan_results.txt` - Text report
   - `ScriptLog.txt` - Processing log

**When to use this:**
- Quick one-off analysis
- You prefer a graphical interface
- You want to manually select different folders

---

### 2. Command Line Analysis

**Best for:** Running analysis from terminal or scripts

**How to use:**

**If package is installed:**
```bash
catphan-analyze /path/to/dicom/folder
```

**If running without installation:**
```bash
cd /path/to/xvicatphan
python main.py /path/to/dicom/folder
```

**Options:**
```bash
# Specify output directory
catphan-analyze /path/to/dicom/folder --output /path/to/results

# Specify CatPhan model (500 or 504)
catphan-analyze /path/to/dicom/folder --model 504
```

**When to use this:**
- Integrating into scripts or workflows
- Batch processing multiple datasets
- Running on remote/headless systems

---

### 3. Automated DICOM Monitoring (For Production Systems)

**Best for:** Continuous monitoring and automatic analysis of incoming DICOM files

**How to use:**

**If package is installed:**
```bash
catphan-listen /path/to/dicom/receiver
```

**If running without installation:**
```bash
cd /path/to/xvicatphan
python listen_and_analyze.py /path/to/dicom/receiver
```

The program monitors the specified folder continuously:
1. When new DICOM files appear, it automatically:
   - Detects the new files
   - Waits for the transfer to complete
   - Runs the analysis
   - Saves results in the same folder
2. Press Ctrl+C to stop monitoring

**Configuration:**
The listener checks for new folders every 5 seconds (configurable in the script).

**When to use this:**
- QA systems that receive DICOM files automatically
- Network folders that receive scans
- Production environments with automated workflows
- When you want "set it and forget it" automation

**Example setup:**
```
Your DICOM Receiver Folder:
├── folder1/          # Analyzed automatically when complete
│   ├── image1.dcm
│   ├── image2.dcm
│   ├── ...
│   ├── CatPhan_results.png  # Created automatically
│   └── CatPhan_results.txt
├── folder2/          # Analyzed when it appears
└── folder3/          # Waiting for new scans...
```

---

## Using the Package in Your Python Code

If you want to integrate the analysis into your own Python scripts:

```python
from catphan_analysis import CatPhanAnalyzer

# Create analyzer
analyzer = CatPhanAnalyzer('/path/to/dicom/files')

# Open log file
analyzer.open_log()

# Run analysis
results = analyzer.analyze()

# Generate output files
analyzer.generate_report()

# Close log
analyzer.close_log()

# Access specific results
print(f"MTF 10%: {results['ctp528']['mtf_10']:.3f} lp/mm")
print(f"Uniformity: {results['ctp486']['uniformity_percent']:.2f}%")
```

See `examples.py` for more detailed usage patterns.

---

## Output Files

All methods produce the same output files:

1. **CatPhan_results.png**
   - 4 analysis plots: CTP528 resolution, MTF curve, CTP404 contrast, CTP486 uniformity
   - 9 line pair profile plots
   - Color-coded ROI overlays

2. **CatPhan_results.txt**
   - Summary of all measurements
   - HU values for each material
   - MTF values at 10%, 30%, 50%, 80%
   - Uniformity measurements
   - Spatial scaling and slice thickness

3. **ScriptLog.txt**
   - Detailed processing log
   - Timestamps and processing steps
   - Useful for troubleshooting

---

## Troubleshooting

**Problem:** "Cannot locate CTP528 module"
- **Solution:** DICOM files may not contain a complete CatPhan scan. Verify your DICOM series.

**Problem:** Analysis produces unexpected results
- **Solution:** Check that:
  - Files are from a CatPhan-500 or 504 phantom
  - The scan covers all three modules (CTP404, CTP486, CTP528)
  - Slice thickness is 2-2.5mm

**Problem:** Listener doesn't detect new files
- **Solution:** 
  - Ensure files are completely transferred before analysis starts
  - Check folder permissions
  - Verify the path is correct

---

## Tips for Best Results

1. **Use consistent scan protocols:** 120 kVp, 2-2.5mm slices
2. **Center the phantom:** Improves automatic detection
3. **Include all modules:** Scan should cover ~120mm along the phantom axis
4. **Check the log file:** If results look wrong, review `ScriptLog.txt` for clues
5. **Use the GUI first:** Try `select_and_analyze.py` on a known-good dataset before setting up automation

---

## Need More Help?

- See `QUICK_REFERENCE.md` for code examples
- See `README.md` for detailed package documentation
- Check `examples.py` for advanced usage patterns
- Review `CLASS_ARCHITECTURE.md` to understand the package structure
