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
        self.scaling_points = None  # Will be set by analyzer
        
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
    
    def calculate_spatial_scaling(self, ct_point, cb_point):
        """
        Calculate X and Y scaling using geometric features.
        
        Full implementation from ScalingXY_CTP404 in original processDICOMcat.py
        
        Args:
            ct_point: Top air ROI center from rotation calculation
            cb_point: Bottom air ROI center from rotation calculation
            
        Returns:
            Tuple of (x_scale_cm, y_scale_cm, scaling_points)
        """
        from scipy.interpolate import interpn
        from scipy.signal import find_peaks
        
        idx = self.slice_index
        
        # 3 slice averaging
        im1 = self.dicom_set[idx].pixel_array
        im2 = self.dicom_set[idx+1].pixel_array
        im3 = self.dicom_set[idx-1].pixel_array
        im = (im1 + im2 + im3) / 3
        
        # Get image size and pixel spacing
        sz = (self.dicom_set[idx].Rows, self.dicom_set[idx].Columns)
        space = self.dicom_set[idx].PixelSpacing
        
        # Index for x and y pixel positions
        x = np.linspace(0, (sz[0]-1), sz[0])
        y = np.linspace(0, (sz[1]-1), sz[1])
        
        # Get center from averaging top and bottom air ROI centers
        cmid = [(ct_point[0] + cb_point[0])/2, (ct_point[1] + cb_point[1])/2]
        
        # Get coordinates through center of top and bottom ROIs
        r = 70  # Radius of circle passing through ROI centers
        t_offset = self.rotation_offset
        
        xscale_xcoord = [cmid[0] - r/space[0]*np.cos(t_offset*2*np.pi/360),
                        cmid[0] + r/space[0]*np.cos(t_offset*2*np.pi/360)]
        xscale_ycoord = [cmid[1] - r/space[0]*np.sin(t_offset*2*np.pi/360),
                        cmid[1] + r/space[0]*np.sin(t_offset*2*np.pi/360)]
        l = np.sqrt((xscale_xcoord[1]-xscale_xcoord[0])**2 + 
                   (xscale_ycoord[1]-xscale_ycoord[0])**2)
        
        # Create profiles through air ROIs
        n = 150
        xtmp = np.linspace(xscale_xcoord[0], xscale_xcoord[1], n)
        ytmp = np.linspace(xscale_ycoord[0], xscale_ycoord[1], n)
        ltmp = np.linspace(0, l, n)
        ftmp = np.zeros(len(xtmp))
        
        for i in range(len(xtmp)):
            ftmp[i] = interpn((x, y), im, [ytmp[i], xtmp[i]])
        
        f1 = ftmp
        pts = [xtmp, ytmp]
        
        # Repeat for perpendicular direction (left/right ROIs)
        t_offset = t_offset + 90
        xscale_xcoord = [cmid[0] - r/space[0]*np.cos(t_offset*2*np.pi/360),
                        cmid[0] + r/space[0]*np.cos(t_offset*2*np.pi/360)]
        xscale_ycoord = [cmid[1] - r/space[0]*np.sin(t_offset*2*np.pi/360),
                        cmid[1] + r/space[0]*np.sin(t_offset*2*np.pi/360)]
        
        xtmp = np.linspace(xscale_xcoord[0], xscale_xcoord[1], n)
        ytmp = np.linspace(xscale_ycoord[0], xscale_ycoord[1], n)
        ftmp = np.zeros(len(xtmp))
        
        for i in range(len(xtmp)):
            ftmp[i] = interpn((x, y), im, [ytmp[i], xtmp[i]])
        
        f2 = ftmp
        pts.extend([xtmp, ytmp])
        
        # Take derivatives
        df1 = np.diff(f1)
        df2 = np.diff(f2)
        
        # Find inflection points - try progressively lower thresholds
        peaks1 = None
        peaks2 = None
        
        for h in [40, 30, 20, 10, 5]:
            try:
                peaks_max1, _ = find_peaks(df1, height=h)
                peaks_min1, _ = find_peaks(-df1, height=h)
                peaks_max2, _ = find_peaks(df2, height=h)
                peaks_min2, _ = find_peaks(-df2, height=h)
                
                peaks1 = np.hstack((peaks_max1, peaks_min1))
                peaks1 = np.array(sorted(peaks1))
                peaks2 = np.hstack((peaks_max2, peaks_min2))
                peaks2 = np.array(sorted(peaks2))
                
                # Check if we have enough peaks (need at least 2 for each)
                if len(peaks1) >= 2 and len(peaks2) >= 2:
                    break
            except:
                continue
        
        # If we still don't have enough peaks, raise an error with diagnostic info
        if peaks1 is None or len(peaks1) < 2 or len(peaks2) < 2:
            raise ValueError(
                f"Could not find enough peaks for spatial scaling calculation. "
                f"Found {len(peaks1) if peaks1 is not None else 0} peaks in direction 1, "
                f"{len(peaks2) if peaks2 is not None else 0} peaks in direction 2. "
                f"Derivative ranges: df1=[{df1.min():.1f}, {df1.max():.1f}], "
                f"df2=[{df2.min():.1f}, {df2.max():.1f}]"
            )
        
        # Calculate scaling from edge-to-edge distances
        xscale1 = np.abs((ltmp[peaks1[0]] - ltmp[peaks1[len(peaks1)-2]])) * space[0]
        xscale2 = np.abs((ltmp[peaks1[1]] - ltmp[peaks1[len(peaks1)-1]])) * space[0]
        yscale1 = np.abs((ltmp[peaks2[0]] - ltmp[peaks2[len(peaks2)-2]])) * space[0]
        yscale2 = np.abs((ltmp[peaks2[1]] - ltmp[peaks2[len(peaks2)-1]])) * space[0]
        
        # Average and convert to cm
        x_scale = ((xscale1 + xscale2) / 2) / 10
        y_scale = ((yscale1 + yscale2) / 2) / 10
        
        self.scaling_results = {
            'x_scale_cm': x_scale,
            'y_scale_cm': y_scale
        }
        self.scaling_points = pts
        
        return x_scale, y_scale, pts
    
    def measure_slice_thickness(self):
        """
        Measure slice thickness using the wire ramp.
        
        Returns:
            Slice thickness in mm
        """
        from ..utils.geometry import CatPhanGeometry
        
        # Use non-averaged image for slice thickness
        im = self.dicom_set[self.slice_index].pixel_array
        space = self.dicom_set[self.slice_index].PixelSpacing
        
        # Calculate slice thickness using wire ramp analysis
        thickness = CatPhanGeometry.calculate_slice_thickness(im, space, self.center)
        
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
        thickness = self.measure_slice_thickness()
        
        # Note: spatial scaling is calculated separately by the analyzer
        # using rotation points from find_rotation()
        
        return {
            'contrast_rois': contrast_results,
            'low_contrast_visibility': lcv,
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
    
    def get_plot_data(self):
        """
        Get data needed for plotting visualizations.
        
        Returns:
            Dictionary with plot data including ROI coordinates,
            scaling points, and outer boundary
        """
        from ..utils.geometry import CatPhanGeometry
        
        if not self.results:
            raise ValueError("Analysis must be run before getting plot data")
        
        # Get outer boundary for phantom visualization
        geometry = CatPhanGeometry()
        _, outer_boundary = geometry.find_center(self.averaged_image)
        
        # Get scaling points (if calculated)
        pts = self.scaling_points if self.scaling_points else [[], [], [], []]
        
        return {
            'roi_coordinates': self.roi_coordinates,
            'scaling_points': pts,
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
        for roi_data in self.results:
            roi_num, material, mean, std = roi_data
            summary[f"ROI {roi_num} ({material})"] = f"{mean:.1f} ± {std:.1f} HU"
        
        if self.scaling_results:
            summary["X Scale"] = f"{self.scaling_results['x_scale_cm']:.2f} cm"
            summary["Y Scale"] = f"{self.scaling_results['y_scale_cm']:.2f} cm"
        
        if self.slice_thickness:
            summary["Slice Thickness"] = f"{self.slice_thickness:.2f} mm"
        
        return summary
