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

from catphan_analysis import CatPhanAnalyzer


def select_folder():
    """
    Open a folder selection dialog.
    
    Returns:
        Path object of selected folder, or None if cancelled
    """
    # Create root window but keep it hidden
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    
    # Open folder selection dialog
    folder_path = filedialog.askdirectory(
        title='Select folder containing DICOM files',
        mustexist=True
    )
    
    # Clean up
    root.destroy()
    
    if folder_path:
        return Path(folder_path)
    return None


def main():
    """
    Main function for GUI-based folder selection and analysis.
    """
    print("\n" + "="*60)
    print("CatPhan Analysis - Folder Selection")
    print("="*60 + "\n")
    print("Opening folder selection dialog...")
    
    # Get folder from user
    dicom_path = select_folder()
    
    if not dicom_path:
        print("\nNo folder selected. Exiting.")
        return 1
    
    print(f"\nSelected folder: {dicom_path}")
    
    # Validate that folder exists and contains files
    if not dicom_path.exists():
        print(f"Error: Selected path does not exist: {dicom_path}")
        return 1
    
    if not any(dicom_path.iterdir()):
        print(f"Error: Selected folder is empty: {dicom_path}")
        return 1
    
    # Create analyzer (output will be saved to same folder)
    print("\n" + "="*60)
    print("Starting Analysis")
    print("="*60 + "\n")
    
    analyzer = CatPhanAnalyzer(
        dicom_path=dicom_path,
        output_path=dicom_path,  # Save results to same folder
        catphan_model='500'
    )
    
    try:
        # Open log file
        analyzer.open_log()
        
        # Run analysis
        print("Loading DICOM files...")
        num_files = analyzer.load_dicom_files()
        
        if num_files == 0:
            print("Error: No DICOM files found in selected folder")
            analyzer.close_log()
            return 1
        
        print("Locating modules...")
        analyzer.locate_modules()
        
        print("Finding centers...")
        analyzer.find_module_centers()
        
        print("Finding rotation...")
        analyzer.find_rotation()
        
        print("Initializing modules...")
        analyzer.initialize_modules()
        
        print("Running analysis...")
        results = analyzer.analyze()
        
        # Generate report with plots
        print("\nGenerating report...")
        report_path = analyzer.generate_report(include_plots=True)
        
        print(f"\n" + "="*60)
        print("Analysis Complete!")
        print("="*60)
        print(f"\nResults saved to: {dicom_path}")
        print(f"Report: {report_path.name}")
        
        # Close log
        analyzer.close_log()
        
        return 0
        
    except Exception as e:
        print(f"\nError during analysis: {e}")
        import traceback
        traceback.print_exc()
        
        # Close log
        try:
            analyzer.close_log()
        except:
            pass
        
        return 1


if __name__ == "__main__":
    sys.exit(main())
