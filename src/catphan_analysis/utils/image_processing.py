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
        # Default the circle center to the middle of the image when none is supplied.
        if center is None:
            center = (int(w/2), int(h/2))

        # Default the radius to the largest circle that fits inside the image bounds.
        if radius is None:
            radius = min(center[0], center[1], w-center[0], h-center[1])
        
        # `Y` and `X` are broadcast-friendly coordinate grids spanning the image.
        Y, X = np.ogrid[:h, :w]

        # `dist_from_center` stores the Euclidean distance from each pixel to the ROI center.
        dist_from_center = np.sqrt((X - center[0])**2 + (Y - center[1])**2)
        
        # Mark pixels inside the requested radius as part of the circular ROI.
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
        # `x_coords` is the evenly sampled set of x positions along the profile line.
        x_coords = np.linspace(start_point[0], end_point[0], num_points)

        # `y_coords` is the evenly sampled set of y positions along the profile line.
        y_coords = np.linspace(start_point[1], end_point[1], num_points)
        
        # Combine the sampled coordinates into `(row, col)` query points for interpolation.
        coords = np.column_stack([y_coords, x_coords])
        
        # `x_grid` and `y_grid` describe the native pixel lattice of the image.
        x_grid = np.arange(image.shape[1])
        y_grid = np.arange(image.shape[0])
        
        # Interpolate the image intensity at each sampled coordinate along the line.
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
        # Extract the pixel arrays for the requested slice indices.
        images = [dicom_set[idx].pixel_array for idx in indices]

        # Return the element-wise mean image across the selected slices.
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
        # `vmin` is the lower bound of the requested display window.
        vmin = level - window / 2

        # `vmax` is the upper bound of the requested display window.
        vmax = level + window / 2
        
        # Clamp the image to the display window and rescale it into 8-bit display space.
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
        # `roi_values` contains only the pixels selected by the ROI mask.
        roi_values = image[mask]
        
        # Return the common descriptive statistics needed by downstream analyses.
        return {
            'mean': np.mean(roi_values),
            'std': np.std(roi_values),
            'min': np.min(roi_values),
            'max': np.max(roi_values),
            'count': len(roi_values)
        }
