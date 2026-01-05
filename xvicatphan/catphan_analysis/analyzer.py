"""
CatPhan Analyzer - Executive Class

Main class that coordinates all CatPhan phantom analysis modules.
"""

import os
import sys
from pathlib import Path
import numpy as np
import pydicom as dicom
import matplotlib.pyplot as plt
import datetime
from typing import Dict, List, Optional

from .modules import CTP404Module, CTP486Module, CTP528Module
from .utils.geometry import CatPhanGeometry, SliceLocator
from .utils.image_processing import ImageProcessor


class CatPhanAnalyzer:
    """
    Executive class for coordinating CatPhan phantom analysis.
    
    This class initializes and manages all analysis module classes,
    coordinates the analysis workflow, and generates reports.
    """
    
    def __init__(self, dicom_path, output_path=None, catphan_model='500'):
        """
        Initialize the CatPhan analyzer.
        
        Args:
            dicom_path: Path to directory containing DICOM files
            output_path: Path for output files (default: same as dicom_path)
            catphan_model: CatPhan model ('500' or '504')
        """
        self.dicom_path = Path(dicom_path)
        self.output_path = Path(output_path) if output_path else self.dicom_path
        self.catphan_model = catphan_model
        
        # Data storage
        self.dicom_set = []
        self.slice_indices = {}
        self.module_centers = {}
        self.rotation_offset = 0.0
        
        # Analysis modules (initialized later)
        self.ctp404 = None
        self.ctp486 = None
        self.ctp528 = None
        
        # Results
        self.results = {}
        
        # Log file
        self.log_file = None
        
    def load_dicom_files(self):
        """
        Load and sort DICOM files from the input directory.
        
        Returns:
            Number of files loaded
        """
        self._log("Loading DICOM files...")
        
        dicom_set_original = []
        slice_locations = []
        
        for root, _, filenames in os.walk(self.dicom_path):
            for filename in filenames:
                # Skip non-DICOM files
                if 'dir' in filename or 'txt' in filename:
                    continue
                
                dcm_path = Path(root, filename)
                
                try:
                    ds = dicom.dcmread(dcm_path, force=True)
                    ds.file_meta.TransferSyntaxUID = dicom.uid.ImplicitVRLittleEndian
                    slice_locations.append(ds.SliceLocation)
                    dicom_set_original.append(ds)
                except Exception as e:
                    self._log(f"Can't import {dcm_path.stem}: {e}")
        
        # Sort by slice location
        slice_locations = np.array(slice_locations)
        sort_indices = (-slice_locations).argsort()
        
        self.dicom_set = [dicom_set_original[i] for i in sort_indices]
        
        self._log(f"Loaded {len(self.dicom_set)} DICOM files")
        
        if len(self.dicom_set) > 0:
            self._log(f"Unit: {self.dicom_set[0].StationName}")
        
        return len(self.dicom_set)
    
    def locate_modules(self):
        """
        Locate the three CatPhan modules in the DICOM series.
        
        Returns:
            Dictionary with slice indices for each module
        """
        self._log("\n--- Locating CatPhan modules ---")
        
        locator = SliceLocator(self.dicom_set)
        self.slice_indices = locator.locate_all_modules()
        
        self._log(f"CTP528 (Line Pairs) found at slice: {self.slice_indices['ctp528']}")
        self._log(f"CTP404 (Contrast) found at slice: {self.slice_indices['ctp404']}")
        self._log(f"CTP486 (Uniformity) found at slice: {self.slice_indices['ctp486']}")
        
        return self.slice_indices
    
    def find_module_centers(self):
        """
        Find the center of each module to correct for setup errors.
        
        Returns:
            Dictionary with center coordinates for each module
        """
        self._log("\n--- Finding module centers ---")
        
        geometry = CatPhanGeometry()
        
        # Get initial images for each module
        idx_528 = self.slice_indices['ctp528']
        idx_404 = self.slice_indices['ctp404']
        idx_486 = self.slice_indices['ctp486']
        
        # Average 3 slices for each module
        im_528 = ImageProcessor.average_slices(self.dicom_set, [idx_528-1, idx_528, idx_528+1])
        im_404 = ImageProcessor.average_slices(self.dicom_set, [idx_404-1, idx_404, idx_404+1])
        im_486 = ImageProcessor.average_slices(self.dicom_set, [idx_486-1, idx_486, idx_486+1])
        
        # Find centers
        c_528, _ = geometry.find_center(im_528)
        c_404, _ = geometry.find_center(im_404)
        c_486, _ = geometry.find_center(im_486)
        
        self.module_centers = {
            'ctp528': c_528,
            'ctp404': c_404,
            'ctp486': c_486
        }
        
        self._log(f"CTP528 center: ({c_528[0]:.1f}, {c_528[1]:.1f})")
        self._log(f"CTP404 center: ({c_404[0]:.1f}, {c_404[1]:.1f})")
        self._log(f"CTP486 center: ({c_486[0]:.1f}, {c_486[1]:.1f})")
        
        return self.module_centers
    
    def find_rotation(self):
        """
        Find the rotation of the CatPhan phantom.
        
        Returns:
            Rotation angle in degrees
        """
        self._log("\n--- Finding CatPhan rotation ---")
        
        geometry = CatPhanGeometry()
        im_404 = self.dicom_set[self.slice_indices['ctp404']].pixel_array
        c_404 = self.module_centers['ctp404']
        
        self.rotation_offset, _, _ = geometry.find_rotation(im_404, c_404)
        
        self._log(f"Rotation offset: {self.rotation_offset:.1f} degrees")
        
        return self.rotation_offset
    
    def initialize_modules(self):
        """
        Initialize all analysis module classes.
        """
        self._log("\n--- Initializing analysis modules ---")
        
        # CTP404 - Contrast module
        self.ctp404 = CTP404Module(
            dicom_set=self.dicom_set,
            slice_index=self.slice_indices['ctp404'],
            center=self.module_centers['ctp404'],
            rotation_offset=self.rotation_offset
        )
        
        # CTP486 - Uniformity module
        self.ctp486 = CTP486Module(
            dicom_set=self.dicom_set,
            slice_index=self.slice_indices['ctp486'],
            center=self.module_centers['ctp486']
        )
        
        # CTP528 - Resolution module
        self.ctp528 = CTP528Module(
            dicom_set=self.dicom_set,
            slice_index=self.slice_indices['ctp528'],
            center=self.module_centers['ctp528'],
            rotation_offset=self.rotation_offset
        )
        
        self._log("All modules initialized successfully")
    
    def analyze(self):
        """
        Run complete analysis of all modules.
        
        Returns:
            Dictionary with all results
        """
        if not self.dicom_set:
            self.load_dicom_files()
        
        if not self.slice_indices:
            self.locate_modules()
        
        if not self.module_centers:
            self.find_module_centers()
            self.find_rotation()
        
        if not self.ctp404:
            self.initialize_modules()
        
        # Analyze each module
        self._log("\n\n=== BEGINNING ANALYSIS ===\n")
        
        self._log("--- Analyzing CTP404 (Contrast/Scaling) ---")
        results_404 = self.ctp404.analyze()
        
        self._log("\n--- Analyzing CTP486 (Uniformity) ---")
        results_486 = self.ctp486.analyze()
        
        self._log("\n--- Analyzing CTP528 (Resolution) ---")
        results_528 = self.ctp528.analyze()
        
        # Compile results
        self.results = {
            'ctp404': results_404,
            'ctp486': results_486,
            'ctp528': results_528,
            'metadata': {
                'unit': self.dicom_set[0].StationName,
                'study_date': self.dicom_set[0].StudyDate,
                'study_time': self.dicom_set[0].StudyTime
            }
        }
        
        self._log("\n=== ANALYSIS COMPLETE ===\n")
        
        return self.results
    
    def generate_report(self, include_plots=True):
        """
        Generate a text report and optional plots.
        
        Args:
            include_plots: Whether to generate plots
            
        Returns:
            Path to the report file
        """
        if not self.results:
            raise ValueError("Analysis must be run before generating report")
        
        self._log("\n--- Generating report ---")
        
        # Create report filename
        ds = self.dicom_set[0]
        date_str = f"{ds.StudyDate[0:4]}-{ds.StudyDate[4:6]}-{ds.StudyDate[6:8]}"
        time_str = f"{ds.StudyTime[0:2]}:{ds.StudyTime[2:4]}:{ds.StudyTime[4:6]}"
        unit_name = ds.StationName
        
        report_filename = f"CatPhan_{unit_name}_{date_str}.txt"
        report_path = self.output_path / report_filename
        
        # Write report
        with open(report_path, 'w') as f:
            f.write("CatPhan Analysis Script Results\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Date: {date_str}\n")
            f.write(f"Time: {time_str}\n")
            f.write(f"Unit: {unit_name}\n\n")
            
            # CTP404 Results
            f.write("----- Module 404 (Contrast Circles) -----\n")
            f.write("ROI,Material,Mean,STD\n")
            for roi_data in self.results['ctp404']['contrast_rois']:
                f.write(f"{roi_data[0]},{roi_data[1]},{roi_data[2]:.1f},{roi_data[3]:.1f}\n")
            
            f.write(f"\nLow contrast visibility: {self.results['ctp404']['low_contrast_visibility']:.3f} %\n")
            f.write(f"X Scale: {self.results['ctp404']['x_scale_cm']:.2f} cm\n")
            f.write(f"Y Scale: {self.results['ctp404']['y_scale_cm']:.2f} cm\n")
            f.write(f"Slice thickness: {self.results['ctp404']['slice_thickness_mm']:.2f} mm\n\n")
            
            # CTP486 Results
            f.write("----- Module 486 (Uniformity) -----\n")
            f.write("ROI,Mean,STD\n")
            for region_data in self.results['ctp486']['regions']:
                f.write(f"{region_data[0]},{region_data[1]:.1f},{region_data[2]:.1f}\n")
            f.write(f"Uniformity: {self.results['ctp486']['uniformity_percent']:.2f} %\n\n")
            
            # CTP528 Results
            f.write("----- Module 528 (Line Pairs) -----\n")
            f.write(f"10% MTF: {self.results['ctp528']['mtf_10']:.3f} lp/mm\n")
            f.write(f"30% MTF: {self.results['ctp528']['mtf_30']:.3f} lp/mm\n")
            f.write(f"50% MTF: {self.results['ctp528']['mtf_50']:.3f} lp/mm\n")
            f.write(f"80% MTF: {self.results['ctp528']['mtf_80']:.3f} lp/mm\n")
        
        self._log(f"Report saved: {report_path}")
        
        # Generate plots if requested
        if include_plots:
            plot_path = self._generate_plots()
            self._log(f"Plots saved: {plot_path}")
        
        return report_path
    
    def _generate_plots(self):
        """
        Generate visualization plots of the analysis.
        
        Returns:
            Path to the plot file
        """
        # Placeholder for plot generation
        # Would create matplotlib figures showing the modules and results
        
        ds = self.dicom_set[0]
        date_str = f"{ds.StudyDate[0:4]}-{ds.StudyDate[4:6]}-{ds.StudyDate[6:8]}"
        unit_name = ds.StationName
        
        plot_filename = f"CatPhan_{unit_name}_{date_str}.png"
        plot_path = self.output_path / plot_filename
        
        # Create basic plot structure
        fig, axes = plt.subplots(2, 2, figsize=(15, 15))
        fig.suptitle(f'CatPhan Analysis - {unit_name}', fontsize=16)
        
        # Close the figure
        plt.savefig(plot_path)
        plt.close()
        
        return plot_path
    
    def _log(self, message):
        """
        Write a message to the log file and print to console.
        
        Args:
            message: Message to log
        """
        print(message)
        
        if self.log_file:
            with open(self.log_file, 'a') as f:
                f.write(message + '\n')
    
    def open_log(self, log_filename='ScriptLog.txt'):
        """
        Open a log file for writing.
        
        Args:
            log_filename: Name of the log file
        """
        self.log_file = self.output_path / log_filename
        
        with open(self.log_file, 'w') as f:
            f.write('CatPhan Analysis Script Log\n')
            f.write(f'Date/Time: {datetime.datetime.now()}\n')
            f.write(f'Path: {self.dicom_path}\n')
            f.write('=' * 60 + '\n\n')
    
    def close_log(self):
        """Close the log file."""
        if self.log_file:
            self._log("\n\nAnalysis complete.")
            self.log_file = None
