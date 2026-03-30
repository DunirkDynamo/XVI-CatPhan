"""
GUI-based folder selection and CatPhan analysis.

This script provides a graphical folder selection dialog, allowing users
to choose a directory containing DICOM files for analysis. Results are
saved to the selected folder.
"""

import sys
import tkinter as tk
from tkinter import filedialog
from pathlib import Path

from catphan_analysis.analyzer import CatPhanAnalyzer


def select_folder():
    """
    Open a folder selection dialog.
    
    Returns:
        Path object of selected folder, or None if cancelled
    """
    # Create the Tk root window solely to host the folder picker dialog.
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    
    # Ask the user to choose the folder that contains the DICOM study.
    folder_path = filedialog.askdirectory(
        title='Select folder containing DICOM files',
        mustexist=True
    )
    
    # Destroy the temporary root window immediately after the dialog closes.
    root.destroy()
    
    # Convert a successful selection to a `Path`; return `None` when cancelled.
    if folder_path:
        return Path(folder_path)
    return None


def main():
    """
    Run the GUI-based folder picker and launch analysis.

    Returns:
        Process exit code where `0` indicates success and `1` indicates failure.
    """
    # Print a short banner so the console output is easy to follow.
    print("\n" + "="*60)
    print("CatPhan Analysis - Folder Selection")
    print("="*60 + "\n")
    print("Opening folder selection dialog...")
    
    # Prompt the user to choose the DICOM folder to analyze.
    dicom_path = select_folder()
    
    if not dicom_path:
        print("\nNo folder selected. Exiting.")
        return 1
    
    print(f"\nSelected folder: {dicom_path}")
    
    # Validate that the selected folder is still present and non-empty.
    if not dicom_path.exists():
        print(f"Error: Selected path does not exist: {dicom_path}")
        return 1
    
    if not any(dicom_path.iterdir()):
        print(f"Error: Selected folder is empty: {dicom_path}")
        return 1
    
    # Build the analyzer and keep all outputs in the selected source folder.
    print("\n" + "="*60)
    print("Starting Analysis")
    print("="*60 + "\n")
    
    analyzer = CatPhanAnalyzer(
        dicom_path=dicom_path,
        output_path=dicom_path,  # Save results to same folder
        catphan_model='500'
    )
    
    try:
        # Open the persistent analysis log before the workflow begins.
        analyzer.open_log()

        # Load the DICOM files explicitly so the GUI entrypoint can fail fast
        # with a clear message if the selected folder does not contain usable data.
        print("Loading DICOM files...")
        num_files = analyzer.load_dicom_files()

        if num_files == 0:
            print("Error: No DICOM files found in selected folder")
            analyzer.close_log()
            return 1

        # Run the main analysis after a valid DICOM series has been confirmed.
        print("Running analysis (auto-locating modules and detecting rotation)...")
        analyzer.analyze()
        
        # Generate the final report bundle, including plots for GUI-driven use.
        print("\nGenerating report...")
        report_path = analyzer.generate_report(include_plots=True)
        
        print(f"\n" + "="*60)
        print("Analysis Complete!")
        print("="*60)
        print(f"\nResults saved to: {dicom_path}")
        print(f"Report: {report_path.name}")
        
        # Close the analysis log on the success path.
        analyzer.close_log()
        
        return 0
        
    except Exception as e:
        # Print the exception and traceback so troubleshooting is possible from the console.
        print(f"\nError during analysis: {e}")
        import traceback
        traceback.print_exc()
        
        # Best-effort log cleanup keeps the log file from staying open after errors.
        try:
            analyzer.close_log()
        except Exception:
            pass
        
        return 1


if __name__ == "__main__":
    sys.exit(main())
