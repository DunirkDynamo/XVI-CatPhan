"""
Geometry utilities for CatPhan phantom analysis.

Provides functions for finding phantom centers, rotations, and geometric measurements.
"""

import numpy as np
from scipy.interpolate import interpn
from scipy.signal import find_peaks


class CatPhanGeometry:
    """
    Handles geometric calculations for CatPhan phantom positioning.
    """
    
    @staticmethod
    def find_center(image, threshold=400):
        """
        Find the center of the CatPhan phantom in an image.
        
        Args:
            image: 2D numpy array of the image
            threshold: HU threshold for edge detection
            
        Returns:
            Tuple of (center_coords, outer_boundary_coords)
        """
        sz = np.array(image.shape)
        matrix_c = (np.round(sz[0]/2), np.round(sz[1]/2))
        
        # Get profiles through center
        px = image[int(matrix_c[0]), :]
        py = image[:, int(matrix_c[1])]
        
        # Find edges of CatPhan
        offset = 1
        
        try:
            x1 = next(x for x, val in enumerate(px) if val > threshold) + offset
            y1 = next(x for x, val in enumerate(py) if val > threshold) - offset
            x2 = next(x for x, val in reversed(list(enumerate(px))) if val > threshold) + offset
            y2 = next(x for x, val in reversed(list(enumerate(py))) if val > threshold) - offset
        except:
            # Try lower threshold
            threshold = 300
            x1 = next(x for x, val in enumerate(px) if val > threshold) + offset
            y1 = next(x for x, val in enumerate(py) if val > threshold) - offset
            x2 = next(x for x, val in reversed(list(enumerate(px))) if val > threshold) + offset
            y2 = next(x for x, val in reversed(list(enumerate(py))) if val > threshold) - offset
        
        # Calculate center and outer radius
        szx = x2 - x1
        szy = y2 - y1
        
        center = [(x1 + x2) / 2, (y1 + y2) / 2]
        outer_r = (szx + szy) / 4
        
        # Create outer boundary for visualization
        t = np.linspace(0, 2*np.pi, 100)
        outer_x = outer_r * np.cos(t) + center[0]
        outer_y = outer_r * np.sin(t) + center[1]
        
        return center, [outer_x, outer_y]
    
    @staticmethod
    def find_rotation(image, center, search_radius=58.5):
        """
        Find the rotation angle of the CatPhan phantom.
        
        Uses the air ROIs in the CTP404 module to determine rotation.
        
        Args:
            image: 2D numpy array of the image
            center: Center coordinates (x, y)
            search_radius: Radius to search for air ROIs in mm
            
        Returns:
            Tuple of (rotation_angle_degrees, top_point, bottom_point)
        """
        # This would implement the FindCTP404Rotation logic
        # Simplified placeholder
        
        # In the real implementation, we'd search for air ROIs
        # and calculate the angle from their positions
        
        # For now, return a placeholder
        rotation_angle = 0.0
        top_point = (center[0], center[1] + search_radius)
        bottom_point = (center[0], center[1] - search_radius)
        
        return rotation_angle, top_point, bottom_point
    
    @staticmethod
    def find_slice_ctp528(dicom_set, expected_slice=86):
        """
        Find the slice containing the CTP528 line pair module.
        
        Args:
            dicom_set: List of DICOM datasets
            expected_slice: Expected slice index to start search
            
        Returns:
            Index of the CTP528 slice
        """
        # Get image info from arbitrary slice
        idx_tmp = min(10, len(dicom_set) - 1)
        sz = (dicom_set[idx_tmp].Rows, dicom_set[idx_tmp].Columns)
        space = dicom_set[idx_tmp].PixelSpacing
        
        # Start search at expected location
        z_tmp = min(expected_slice, len(dicom_set) - 1)
        
        # Find center of phantom
        outer_c, _ = CatPhanGeometry.find_center(dicom_set[z_tmp].pixel_array)
        
        # Search for line pairs - simplified implementation
        # Real implementation would search through slices looking for
        # characteristic line pair patterns
        
        # For now, return the expected slice
        return z_tmp
    
    @staticmethod
    def calculate_slice_thickness(image, pixel_spacing, center):
        """
        Calculate slice thickness using wire ramp.
        
        Args:
            image: 2D numpy array of the image
            pixel_spacing: Pixel spacing in mm
            center: Center coordinates
            
        Returns:
            Slice thickness in mm
        """
        # This would implement the FindSliceThickness logic
        # Simplified placeholder
        
        # Real implementation would analyze the wire ramp pattern
        thickness = 5.0  # Default placeholder
        
        return thickness


class SliceLocator:
    """
    Locates specific modules within a DICOM series.
    """
    
    def __init__(self, dicom_set):
        """
        Initialize slice locator.
        
        Args:
            dicom_set: List of sorted DICOM datasets
        """
        self.dicom_set = dicom_set
        self.ctp528_index = None
        self.ctp404_index = None
        self.ctp486_index = None
        
    def locate_all_modules(self):
        """
        Locate all three CatPhan modules.
        
        Returns:
            Dictionary with slice indices for each module
        """
        # Find CTP528 first (line pairs)
        self.ctp528_index = CatPhanGeometry.find_slice_ctp528(self.dicom_set)
        
        # Calculate other module locations based on CTP528
        # Distances for CatPhan-500
        d_CTP404 = -30   # mm from CTP528
        d_CTP486 = -110  # mm from CTP528
        
        # Get slice thickness and direction
        z = self.dicom_set[self.ctp528_index].SliceThickness
        z1 = self.dicom_set[self.ctp528_index].SliceLocation
        z2 = self.dicom_set[self.ctp528_index + 1].SliceLocation
        
        # Determine slice direction
        if (z2 - z1) > 0:
            # Z is increasing
            self.ctp404_index = int(self.ctp528_index + float(d_CTP404) / z)
            self.ctp486_index = int(self.ctp528_index + float(d_CTP486) / z)
        else:
            # Z is decreasing
            self.ctp404_index = int(self.ctp528_index - float(d_CTP404) / z)
            self.ctp486_index = int(self.ctp528_index - float(d_CTP486) / z)
        
        return {
            'ctp528': self.ctp528_index,
            'ctp404': self.ctp404_index,
            'ctp486': self.ctp486_index
        }
