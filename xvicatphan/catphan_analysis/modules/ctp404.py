"""
CTP404 Module - Contrast and Spatial Linearity Analysis

This module handles the analysis of the CTP404 sensitometry module,
including contrast measurements, HU accuracy, and spatial scaling.
"""

import numpy as np
from typing import Tuple, List, Dict


class CTP404Module:
    """
    Analysis class for CTP404 contrast and linearity module.
    
    This module measures HU values for different materials, calculates
    low contrast visibility, and verifies spatial scaling/linearity.
    """
    
    # Material names for each ROI
    MATERIALS = [
        'Delrin', 'none', 'Acrylic', 'Air', 'Polystyrene',
        'LDPE', 'PMP', 'Teflon', 'Air2'
    ]
    
    # ROI angles (degrees) relative to phantom rotation
    ROI_ANGLES = [0, 30, 60, 90, 120, 180, -120, -60, -90]
    
    def __init__(self, dicom_set, slice_index, center, rotation_offset):
        """
        Initialize CTP404 analysis module.
        
        Args:
            dicom_set: List of DICOM dataset objects
            slice_index: Index of the CTP404 slice in the dataset
            center: Tuple (x, y) of module center coordinates
            rotation_offset: Rotation offset in degrees for angular correction
        """
        self.dicom_set = dicom_set
        self.slice_index = slice_index
        self.center = center
        self.rotation_offset = rotation_offset
        self.averaged_image = None
        self.results = []
        self.roi_coordinates = None
        self.scaling_results = None
        self.slice_thickness = None
        
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
    
    def analyze_contrast(self):
        """
        Analyze contrast ROIs and calculate HU values.
        
        Returns:
            List of results: [ROI_number, material_name, mean_HU, std_HU]
        """
        if self.averaged_image is None:
            self.prepare_image()
        
        im = self.averaged_image
        sz = (self.dicom_set[self.slice_index].Rows, 
              self.dicom_set[self.slice_index].Columns)
        space = self.dicom_set[self.slice_index].PixelSpacing
        
        # ROI parameters
        h, w = im.shape[:2]
        r = 3.5 / space[0]  # ROI radius in pixels
        ring_r = 58.5 / space[0]  # Distance from center in pixels
        
        # Create masks and calculate statistics for each ROI
        results = []
        roi_coords = []
        
        for i, (angle, material) in enumerate(zip(self.ROI_ANGLES, self.MATERIALS)):
            # Calculate ROI center
            angle_rad = np.radians(angle + self.rotation_offset)
            cx = ring_r * np.cos(angle_rad) + self.center[0]
            cy = ring_r * np.sin(angle_rad) + self.center[1]
            
            # Create circular mask
            mask = self._create_circular_mask(h, w, (cx, cy), r)
            
            # Calculate statistics
            mean_hu = np.mean(im[mask])
            std_hu = np.std(im[mask])
            
            results.append([i+1, material, mean_hu, std_hu])
            
            # Store ROI coordinates for visualization
            t = np.linspace(0, 2*np.pi, 100)
            roi_x = r * np.cos(t) + cx
            roi_y = r * np.sin(t) + cy
            roi_coords.append((roi_x, roi_y))
        
        self.results = results
        self.roi_coordinates = roi_coords
        
        return results
    
    def calculate_low_contrast_visibility(self):
        """
        Calculate low contrast visibility metric.
        
        Returns:
            Low contrast visibility value
        """
        if not self.results:
            self.analyze_contrast()
        
        # LCV based on Polystyrene (index 4) and LDPE (index 5)
        polystyrene = self.results[4]
        ldpe = self.results[5]
        
        lcv = 3.25 * (polystyrene[3] + ldpe[3]) / (polystyrene[2] - ldpe[2])
        
        return lcv
    
    def calculate_spatial_scaling(self):
        """
        Calculate X and Y scaling using geometric features.
        
        Returns:
            Tuple of (x_scale_cm, y_scale_cm, center_points)
        """
        # This would implement the ScalingXY_CTP404 logic
        # Simplified placeholder
        ds = self.dicom_set[self.slice_index]
        space = ds.PixelSpacing
        
        # Expected distance between features in mm
        expected_distance = 100  # mm
        
        # Calculate scaling (placeholder)
        scale_x = expected_distance / 10  # convert to cm
        scale_y = expected_distance / 10
        
        self.scaling_results = {
            'x_scale_cm': scale_x,
            'y_scale_cm': scale_y
        }
        
        return scale_x, scale_y, []
    
    def measure_slice_thickness(self):
        """
        Measure slice thickness using the wire ramp.
        
        Returns:
            Slice thickness in mm
        """
        # Use non-averaged image for slice thickness
        im = self.dicom_set[self.slice_index].pixel_array
        space = self.dicom_set[self.slice_index].PixelSpacing
        
        # Simplified calculation - full version would analyze wire ramp
        # This is a placeholder
        thickness = self.dicom_set[self.slice_index].SliceThickness
        
        self.slice_thickness = thickness
        return thickness
    
    def analyze(self):
        """
        Perform complete analysis of CTP404 module.
        
        Returns:
            Dictionary containing all analysis results
        """
        # Run all analyses
        contrast_results = self.analyze_contrast()
        lcv = self.calculate_low_contrast_visibility()
        x_scale, y_scale, _ = self.calculate_spatial_scaling()
        thickness = self.measure_slice_thickness()
        
        return {
            'contrast_rois': contrast_results,
            'low_contrast_visibility': lcv,
            'x_scale_cm': x_scale,
            'y_scale_cm': y_scale,
            'slice_thickness_mm': thickness
        }
    
    def _create_circular_mask(self, h, w, center, radius):
        """
        Create a circular boolean mask.
        
        Args:
            h: Image height
            w: Image width
            center: Tuple (x, y) of circle center
            radius: Circle radius in pixels
            
        Returns:
            Boolean array mask
        """
        if center is None:
            center = (int(w/2), int(h/2))
        if radius is None:
            radius = min(center[0], center[1], w-center[0], h-center[1])
        
        Y, X = np.ogrid[:h, :w]
        dist_from_center = np.sqrt((X - center[0])**2 + (Y - center[1])**2)
        
        mask = dist_from_center <= radius
        return mask
    
    def get_results_summary(self):
        """
        Get a formatted summary of analysis results.
        
        Returns:
            Dictionary with key measurements
        """
        if not self.results:
            raise ValueError("Analysis must be run before getting results")
        
        summary = {}
        for roi_data in self.results:
            roi_num, material, mean, std = roi_data
            summary[f"ROI {roi_num} ({material})"] = f"{mean:.1f} ± {std:.1f} HU"
        
        if self.scaling_results:
            summary["X Scale"] = f"{self.scaling_results['x_scale_cm']:.2f} cm"
            summary["Y Scale"] = f"{self.scaling_results['y_scale_cm']:.2f} cm"
        
        if self.slice_thickness:
            summary["Slice Thickness"] = f"{self.slice_thickness:.2f} mm"
        
        return summary
