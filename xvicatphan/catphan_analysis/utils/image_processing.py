"""
Image processing utilities for CatPhan analysis.
"""

import numpy as np
from scipy.interpolate import interpn


class ImageProcessor:
    """
    Provides image processing operations for CatPhan analysis.
    """
    
    @staticmethod
    def create_circular_mask(h, w, center=None, radius=None):
        """
        Create a circular boolean mask.
        
        Args:
            h: Image height in pixels
            w: Image width in pixels
            center: Tuple (x, y) of circle center (default: image center)
            radius: Circle radius in pixels (default: maximum inscribed circle)
            
        Returns:
            Boolean array mask of shape (h, w)
        """
        if center is None:
            center = (int(w/2), int(h/2))
        if radius is None:
            radius = min(center[0], center[1], w-center[0], h-center[1])
        
        Y, X = np.ogrid[:h, :w]
        dist_from_center = np.sqrt((X - center[0])**2 + (Y - center[1])**2)
        
        mask = dist_from_center <= radius
        return mask
    
    @staticmethod
    def extract_profile(image, start_point, end_point, num_points=100):
        """
        Extract an intensity profile along a line.
        
        Args:
            image: 2D numpy array
            start_point: (x, y) starting coordinates
            end_point: (x, y) ending coordinates
            num_points: Number of points to sample along the line
            
        Returns:
            Numpy array of intensity values
        """
        x_coords = np.linspace(start_point[0], end_point[0], num_points)
        y_coords = np.linspace(start_point[1], end_point[1], num_points)
        
        # Create coordinate pairs for interpolation
        coords = np.column_stack([y_coords, x_coords])
        
        # Get grid for interpolation
        x_grid = np.arange(image.shape[1])
        y_grid = np.arange(image.shape[0])
        
        # Interpolate values
        profile = interpn((y_grid, x_grid), image, coords, method='linear')
        
        return profile
    
    @staticmethod
    def average_slices(dicom_set, indices):
        """
        Average multiple DICOM slices.
        
        Args:
            dicom_set: List of DICOM datasets
            indices: List of slice indices to average
            
        Returns:
            Averaged image array
        """
        images = [dicom_set[idx].pixel_array for idx in indices]
        return np.mean(images, axis=0)
    
    @staticmethod
    def apply_window_level(image, window, level):
        """
        Apply window/level to an image for display.
        
        Args:
            image: Input image array
            window: Window width in HU
            level: Window center in HU
            
        Returns:
            Windowed image array (0-255)
        """
        vmin = level - window / 2
        vmax = level + window / 2
        
        windowed = np.clip(image, vmin, vmax)
        windowed = ((windowed - vmin) / (vmax - vmin) * 255).astype(np.uint8)
        
        return windowed
    
    @staticmethod
    def calculate_roi_statistics(image, mask):
        """
        Calculate statistics for a masked ROI.
        
        Args:
            image: Input image array
            mask: Boolean mask array
            
        Returns:
            Dictionary with mean, std, min, max
        """
        roi_values = image[mask]
        
        return {
            'mean': np.mean(roi_values),
            'std': np.std(roi_values),
            'min': np.min(roi_values),
            'max': np.max(roi_values),
            'count': len(roi_values)
        }
