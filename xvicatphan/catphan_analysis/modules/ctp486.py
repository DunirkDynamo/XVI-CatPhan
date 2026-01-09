"""
CTP486 Module - Uniformity Analysis

This module handles the analysis of the CTP486 uniformity module,
measuring image uniformity across different regions.
"""

import numpy as np
from typing import Tuple, List, Dict


class CTP486Module:
    """
    Analysis class for CTP486 uniformity module.
    
    This module measures image uniformity by comparing HU values
    in different regions of a homogeneous phantom section.
    """
    
    # Region names
    REGIONS = ['centre', 'north', 'south', 'east', 'west']
    
    def __init__(self, dicom_set, slice_index, center, roi_box_size=15, roi_offset=50):
        """
        Initialize CTP486 analysis module.
        
        Args:
            dicom_set: List of DICOM dataset objects
            slice_index: Index of the CTP486 slice in the dataset
            center: Tuple (x, y) of module center coordinates
            roi_box_size: Size of square ROI boxes in mm
            roi_offset: Offset from center for peripheral ROIs in mm
        """
        self.dicom_set = dicom_set
        self.slice_index = slice_index
        self.center = center
        self.roi_box_size = roi_box_size
        self.roi_offset = roi_offset
        self.averaged_image = None
        self.results = []
        self.roi_coordinates = None
        self.uniformity_percent = None
        
    def prepare_image(self):
        """
        Create 3-slice averaged image for improved SNR.
        
        Returns:
            Averaged image array
        """
        idx = self.slice_index
        im1 = self.dicom_set[idx].pixel_array
        im2 = self.dicom_set[idx+1].pixel_array
        im3 = self.dicom_set[idx-1].pixel_array
        
        self.averaged_image = (im1 + im2 + im3) / 3
        return self.averaged_image
    
    def analyze_uniformity(self):
        """
        Analyze uniformity by measuring HU values in 5 regions.
        
        Returns:
            Tuple of (results_list, composite_mask, roi_coordinates)
        """
        if self.averaged_image is None:
            self.prepare_image()
        
        im = self.averaged_image
        sz = (self.dicom_set[self.slice_index].Rows,
              self.dicom_set[self.slice_index].Columns)
        space = self.dicom_set[self.slice_index].PixelSpacing
        
        # Convert dimensions to pixels
        roi_sz = self.roi_box_size / space[0]
        roi_off = self.roi_offset / space[0]
        outer_c = self.center
        
        # Create masks for each ROI region and store coordinates
        masks = {}
        roi_data = {}
        roi_coords = []  # Store box coordinates as we create them
        half_sz = int(roi_sz / 2)
        
        # Center ROI
        mc = self._create_box_mask(sz, outer_c[0], outer_c[1], roi_sz)
        roi_data['centre'] = im[mc == 1]
        masks['centre'] = mc
        roi_coords.append([
            int(outer_c[0]) - half_sz,
            int(outer_c[0]) + half_sz,
            int(outer_c[1]) - half_sz,
            int(outer_c[1]) + half_sz
        ])
        
        # North ROI (negative Y in image coords = up in display)
        mn = self._create_box_mask(sz, outer_c[0], outer_c[1] - roi_off, roi_sz)
        roi_data['north'] = im[mn == 1]
        masks['north'] = mn
        roi_coords.append([
            int(outer_c[0]) - half_sz,
            int(outer_c[0]) + half_sz,
            int(outer_c[1] - roi_off) - half_sz,
            int(outer_c[1] - roi_off) + half_sz
        ])
        
        # South ROI (positive Y in image coords = down in display)
        ms = self._create_box_mask(sz, outer_c[0], outer_c[1] + roi_off, roi_sz)
        roi_data['south'] = im[ms == 1]
        masks['south'] = ms
        roi_coords.append([
            int(outer_c[0]) - half_sz,
            int(outer_c[0]) + half_sz,
            int(outer_c[1] + roi_off) - half_sz,
            int(outer_c[1] + roi_off) + half_sz
        ])
        
        # East ROI (positive X direction)
        me = self._create_box_mask(sz, outer_c[0] + roi_off, outer_c[1], roi_sz)
        roi_data['east'] = im[me == 1]
        masks['east'] = me
        roi_coords.append([
            int(outer_c[0] + roi_off) - half_sz,
            int(outer_c[0] + roi_off) + half_sz,
            int(outer_c[1]) - half_sz,
            int(outer_c[1]) + half_sz
        ])
        
        # West ROI (negative X direction)
        mw = self._create_box_mask(sz, outer_c[0] - roi_off, outer_c[1], roi_sz)
        roi_data['west'] = im[mw == 1]
        masks['west'] = mw
        roi_coords.append([
            int(outer_c[0] - roi_off) - half_sz,
            int(outer_c[0] - roi_off) + half_sz,
            int(outer_c[1]) - half_sz,
            int(outer_c[1]) + half_sz
        ])
        
        # Calculate statistics for each region
        results = []
        means = []
        
        for region in self.REGIONS:
            mean_val = np.mean(roi_data[region])
            std_val = np.std(roi_data[region])
            results.append([region, mean_val, std_val])
            means.append(mean_val)
        
        # Calculate uniformity metric
        uniformity = (np.max(means) - np.min(means)) / np.max(means) * 100
        results.append(['Uniformity', uniformity, None])
        
        # Create composite mask
        m_total = mc + mn + ms + me + mw
        
        self.results = results
        self.roi_coordinates = roi_coords
        self.uniformity_percent = uniformity
        
        return results, m_total, roi_coords
    
    def _create_box_mask(self, sz, cx, cy, roi_sz):
        """
        Create a square box mask.
        
        Args:
            sz: Image size tuple (rows, cols)
            cx: Center x coordinate
            cy: Center y coordinate
            roi_sz: Size of box in pixels
            
        Returns:
            Boolean mask array
        """
        mask = np.zeros(sz)
        x_start = int(cx - roi_sz/2)
        x_end = int(cx + roi_sz/2)
        y_start = int(cy - roi_sz/2)
        y_end = int(cy + roi_sz/2)
        
        # Ensure indices are within bounds
        x_start = max(0, x_start)
        x_end = min(sz[0], x_end)
        y_start = max(0, y_start)
        y_end = min(sz[1], y_end)
        
        # Use proper numpy indexing: [row, col] = [y, x]
        mask[y_start:y_end, x_start:x_end] = 1
        return mask
    
    def analyze(self):
        """
        Perform complete uniformity analysis.
        
        Returns:
            Dictionary containing analysis results
        """
        results, _, roi_coords = self.analyze_uniformity()
        
        return {
            'regions': results[:-1],  # All except uniformity metric
            'uniformity_percent': self.uniformity_percent,
            'roi_coordinates': roi_coords
        }
    
    def get_plot_data(self):
        """
        Get data needed for plotting visualizations.
        
        Returns:
            Dictionary with plot data including ROI boxes and outer boundary
        """
        from ..utils.geometry import CatPhanGeometry
        
        if not self.results:
            raise ValueError("Analysis must be run before getting plot data")
        
        # Get outer boundary for phantom visualization
        geometry = CatPhanGeometry()
        _, outer_boundary = geometry.find_center(self.averaged_image)
        
        return {
            'roi_boxes': self.roi_coordinates,
            'outer_boundary': outer_boundary
        }
    
    def get_results_summary(self):
        """
        Get a formatted summary of analysis results.
        
        Returns:
            Dictionary with key measurements
        """
        if not self.results:
            raise ValueError("Analysis must be run before getting results")
        
        summary = {}
        for result in self.results[:-1]:  # Exclude uniformity entry
            region, mean, std = result
            summary[f"{region.capitalize()} ROI"] = f"{mean:.1f} ± {std:.1f} HU"
        
        if self.uniformity_percent is not None:
            summary["Uniformity"] = f"{self.uniformity_percent:.2f}%"
        
        return summary
