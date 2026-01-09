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
        
        # Rotation points for CTP404
        self.ct_point = None
        self.cb_point = None
        
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
        
        # For CTP528, use intelligent slice selection (same as original image_selector_CTP528)
        im_528, _, _ = geometry.select_optimal_ctp528_slices(self.dicom_set, idx_528)
        
        # For CTP404 and CTP486, use simple 3-slice averaging
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
        idx_404 = self.slice_indices['ctp404']
        im_404 = self.dicom_set[idx_404].pixel_array
        c_404 = self.module_centers['ctp404']
        space = self.dicom_set[idx_404].PixelSpacing
        
        self.rotation_offset, self.ct_point, self.cb_point = geometry.find_rotation(im_404, c_404, space)
        
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
        
        # Calculate refined center for CTP404 using spatial scaling points
        # This mimics the original script's approach (line 1453 in processDICOMcat.py)
        if self.ct_point is not None and self.cb_point is not None:
            self._log("Calculating refined CTP404 center using spatial scaling...")
            x_scale, y_scale, pts = self.ctp404.calculate_spatial_scaling(self.ct_point, self.cb_point)
            
            # Refine center using scaling points: c_CTP404 = [np.mean([pts[0],pts[2]]),np.mean([pts[1],pts[3]])]
            refined_center = [np.mean([pts[0], pts[2]]), np.mean([pts[1], pts[3]])]
            self._log(f"Original CTP404 center: ({self.module_centers['ctp404'][0]:.1f}, {self.module_centers['ctp404'][1]:.1f})")
            self._log(f"Refined CTP404 center: ({refined_center[0]:.1f}, {refined_center[1]:.1f})")
            
            # Update center and reinitialize CTP404 module with refined center
            self.module_centers['ctp404'] = refined_center
            self.ctp404 = CTP404Module(
                dicom_set=self.dicom_set,
                slice_index=self.slice_indices['ctp404'],
                center=refined_center,
                rotation_offset=self.rotation_offset
            )
            self.ctp404.prepare_image()
            # Restore scaling points since we created a new instance
            self.ctp404.scaling_points = pts
        
        # Analyze each module
        self._log("\n\n=== BEGINNING ANALYSIS ===\n")
        
        self._log("--- Analyzing CTP404 (Contrast/Scaling) ---")
        results_404 = self.ctp404.analyze()
        
        # Add scaling results if we calculated them earlier
        if self.ct_point is not None and self.cb_point is not None:
            results_404['x_scale_cm'] = x_scale
            results_404['y_scale_cm'] = y_scale
            self._log(f"X Scale: {x_scale:.2f} cm")
            self._log(f"Y Scale: {y_scale:.2f} cm")
        
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
            f.write(f"80% MTF: {self.results['ctp528']['mtf_80']:.3f} lp/mm\n\n")
            
            # Misc Results
            f.write("----- Misc -----\n")
            f.write(f"Catphan rotation (deg): {self.rotation_offset:.1f}\n")
        
        self._log(f"Report saved: {report_path}")
        
        # Generate plots if requested
        if include_plots:
            plot_path = self._generate_plots()
            self._log(f"Plots saved: {plot_path}")
        
        return report_path
    
    def _generate_plots(self):
        """
        Generate visualization plots showing DICOM images with ROI overlays.
        
        Recreates the original plotting style from processDICOMcat.py
        
        Returns:
            Path to the plot file
        """
        ds = self.dicom_set[0]
        date_str = f"{ds.StudyDate[0:4]}-{ds.StudyDate[4:6]}-{ds.StudyDate[6:8]}"
        unit_name = ds.StationName
        
        plot_filename = f"CatPhan_{unit_name}_{date_str}.png"
        plot_path = self.output_path / plot_filename
        
        # Window/level settings for display
        window = 1000
        level = 1000
        vmin = int(level - window/2)
        vmax = int(level + window/2)
        
        # Create figure with 2 columns: left has 2x2 grid, right has 9 stacked plots
        fig = plt.figure(figsize=(20, 15))
        gs = fig.add_gridspec(9, 3, width_ratios=[1, 1, 1], hspace=0.3, wspace=0.3)
        
        fig.suptitle(f'Unit: {unit_name}, Window/level: {window}/{level}', fontsize=16)
        
        # Left column - existing 2x2 plots
        # Plot 1: CTP528 Resolution Module (top-left)
        ax1 = fig.add_subplot(gs[0:4, 0])
        
        # Get image and plot data from module
        im_528 = self.ctp528.averaged_image
        plot_data_528 = self.ctp528.get_plot_data()
        
        ax1.imshow(im_528, cmap='gray', vmin=vmin, vmax=vmax)
        ax1.plot(plot_data_528['lpx'], plot_data_528['lpy'], '-r')
        ax1.plot(np.array(plot_data_528['outer_boundary'][0]), 
                np.array(plot_data_528['outer_boundary'][1]), 'r')
        ax1.set_title('CTP528')
        ax1.axis('off')
        
        # Plot 2: CTP528 MTF Curve (top-middle)
        ax2 = fig.add_subplot(gs[0:4, 1])
        
        mtf_data = plot_data_528['mtf_data']
        lp = mtf_data['lp']
        nMTF = mtf_data['nMTF']
        nMTF50 = self.results['ctp528']['mtf_50']
        nMTF10 = self.results['ctp528']['mtf_10']
        
        ax2.plot(lp, nMTF)
        ax2.plot([nMTF50, nMTF10], [0.5, 0.1], 'or', mfc='none')
        ax2.set_title(f'10% MTF = {nMTF10:.3f} lp/mm')
        ax2.set_ylabel('Normalized MTF')
        ax2.set_xlabel('lp/mm')
        ax2.grid()
        
        # Plot 3: CTP404 Contrast Module (bottom-left)
        ax3 = fig.add_subplot(gs[5:9, 0])
        
        im_404 = self.ctp404.averaged_image
        plot_data_404 = self.ctp404.get_plot_data()
        
        ax3.imshow(im_404, cmap='gray', vmin=vmin, vmax=vmax)
        
        # Plot all ROI circles
        roi_coords = plot_data_404['roi_coordinates']
        if roi_coords:
            for roi_x, roi_y in roi_coords:
                ax3.plot(roi_x, roi_y, 'r')
        
        # Plot scaling points
        pts = plot_data_404['scaling_points']
        if pts and len(pts) >= 4 and len(pts[0]) > 0:
            ax3.plot(pts[0], pts[1], 'g')
            ax3.plot(pts[2], pts[3], 'g')
        
        # Plot outer boundary
        ax3.plot(np.array(plot_data_404['outer_boundary'][0]), 
                np.array(plot_data_404['outer_boundary'][1]), 'r')
        
        ax3.set_title('CTP404')
        ax3.axis('off')
        
        # Plot 4: CTP486 Uniformity Module (bottom-middle)
        ax4 = fig.add_subplot(gs[5:9, 1])
        
        im_486 = self.ctp486.averaged_image
        plot_data_486 = self.ctp486.get_plot_data()
        
        ax4.imshow(im_486, cmap='gray', vmin=vmin, vmax=vmax)
        
        # Plot outer boundary
        ax4.plot(np.array(plot_data_486['outer_boundary'][0]), 
                np.array(plot_data_486['outer_boundary'][1]), 'r')
        
        # Plot ROI boxes with different colors
        roi_boxes = plot_data_486['roi_boxes']
        roi_colors = {'centre': 'yellow', 'north': 'cyan', 'south': 'magenta', 
                      'east': 'green', 'west': 'orange'}
        roi_labels = ['Centre', 'North', 'South', 'East', 'West']
        
        if roi_boxes:
            for i, box in enumerate(roi_boxes):
                # box format: [x_start, x_end, y_start, y_end]
                x0, x1, y0, y1 = box
                region_name = self.ctp486.REGIONS[i]
                color = roi_colors[region_name]
                label = roi_labels[i]
                
                ax4.plot([x0, x0], [y0, y1], color=color, linewidth=2, label=label)
                ax4.plot([x1, x1], [y0, y1], color=color, linewidth=2)
                ax4.plot([x0, x1], [y0, y0], color=color, linewidth=2)
                ax4.plot([x0, x1], [y1, y1], color=color, linewidth=2)
        
        ax4.legend(loc='upper right', fontsize=8)
        ax4.set_title('CTP486')
        ax4.axis('off')
        
        # Right column - Line pair profiles (9 stacked plots sharing x-axis)
        profiles = plot_data_528.get('line_pair_profiles')
        if profiles and len(profiles) == 9:
            for i in range(9):
                ax = fig.add_subplot(gs[i, 2])
                ax.plot(profiles[i], 'b-', linewidth=0.8)
                ax.set_ylabel(f'LP{i+1}', fontsize=8)
                ax.tick_params(axis='both', labelsize=7)
                ax.grid(True, alpha=0.3)
                
                # Only show x-axis label on bottom plot
                if i < 8:
                    ax.set_xticklabels([])
                else:
                    ax.set_xlabel('Position', fontsize=8)
        
        # Save figure
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
