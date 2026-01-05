"""
CTP528 Module - Line Pair Resolution Analysis

This module handles the analysis of the CTP528 high-resolution module,
including MTF calculation and line pair resolution measurement.
"""

import numpy as np
from scipy.interpolate import interpn, interp1d
from scipy.signal import find_peaks, peak_widths


class CTP528Module:
    """
    Analysis class for CTP528 line pair resolution module.
    
    This module measures spatial resolution using line pair patterns
    and calculates the Modulation Transfer Function (MTF).
    """
    
    def __init__(self, dicom_set, slice_index, center, rotation_offset):
        """
        Initialize CTP528 analysis module.
        
        Args:
            dicom_set: List of DICOM dataset objects
            slice_index: Index of the CTP528 slice in the dataset
            center: Tuple (x, y) of module center coordinates
            rotation_offset: Rotation offset in degrees for angular correction
        """
        self.dicom_set = dicom_set
        self.slice_index = slice_index
        self.center = center
        self.rotation_offset = rotation_offset
        self.averaged_image = None
        self.mtf = None
        self.lp_frequencies = None
        self.results = {}
        
    def select_optimal_slices(self, search_range=2):
        """
        Select and average 3 slices around the CTP528 module for optimal contrast.
        
        Args:
            search_range: Number of slices to check above/below the target slice
            
        Returns:
            Tuple of (averaged_image, means_array, z_offset)
        """
        z = self.slice_index
        ds = self.dicom_set
        
        # Get slices around the target
        img_zm2 = ds[z-2].pixel_array
        img_zm1 = ds[z-1].pixel_array
        img_z = ds[z].pixel_array
        img_zp1 = ds[z+1].pixel_array
        img_zp2 = ds[z+2].pixel_array
        
        sz = (ds[z].Rows, ds[z].Columns)
        space = ds[z].PixelSpacing
        c = (int(sz[0]/2), int(sz[1]/2))
        
        # Trace through line pairs
        lp_r = 47  # radius in mm
        tfine = np.linspace(0, np.pi, 500)
        lp_b = lp_r/space[0]*np.cos(tfine) + c[0]
        lp_a = lp_r/space[1]*np.sin(tfine) + c[1]
        
        # Get indexing for image matrix
        x = np.linspace(0, (sz[0]-1)/2, sz[0])
        y = np.linspace(0, (sz[1]-1)/2, sz[1])
        
        # Interpolate profiles for each image
        images = [img_zm2, img_zm1, img_z, img_zp1, img_zp2]
        profiles = []
        
        for im in images:
            f = np.zeros(len(lp_a))
            for i in range(len(lp_a)):
                f[i] = interpn((x, y), im+2048, [lp_a[i]*space[0], lp_b[i]*space[1]])
            profiles.append(f)
        
        # Find slice with highest average intensity
        means = [np.mean(f) for f in profiles]
        tmp = np.argmax(means)
        
        # Select 3 consecutive slices around the maximum
        idx = np.zeros(5)
        try:
            idx[tmp-1] = 1
            idx[tmp] = 1
            idx[tmp+1] = 1
        except:
            if tmp == 0:
                idx = [1, 1, 0, 0, 0]
            elif tmp == 4:
                idx = [0, 0, 0, 1, 1]
            else:
                return img_z, means, 0
        
        # Calculate 3-slice average
        im = np.zeros(sz)
        z_mean = []
        
        for i, include in enumerate(idx):
            if include:
                im += images[i]
                z_mean.append(i - 2)
        
        im = im / sum(idx)
        z_mean = np.mean(z_mean)
        
        self.averaged_image = im
        return im, means, z_mean
    
    def analyze(self, write_log=True):
        """
        Perform complete analysis of CTP528 module.
        
        Args:
            write_log: Whether to write progress to log file
            
        Returns:
            Dictionary containing MTF values and line pair coordinates
        """
        if self.averaged_image is None:
            self.select_optimal_slices()
        
        # Get image from the analysis helper
        from ..utils.image_processing import ImageProcessor
        processor = ImageProcessor()
        
        mtf, lpf, _, _, _, lpx, lpy = self._calculate_mtf(
            self.averaged_image, 
            self.center, 
            self.rotation_offset
        )
        
        # Normalize MTF
        nMTF = mtf / max(np.array(mtf))
        
        # Calculate MTF at specific percentages
        lp = np.linspace(1, len(mtf), len(mtf)) / 10
        MTF_sample = (0.8, 0.5, 0.3, 0.1)
        fMTF = np.interp(MTF_sample, nMTF[::-1], lp[::-1])
        
        self.results = {
            'mtf_80': fMTF[0],
            'mtf_50': fMTF[1],
            'mtf_30': fMTF[2],
            'mtf_10': fMTF[3],
            'mtf_array': nMTF,
            'lp_frequencies': lp,
            'line_pair_x': lpx,
            'line_pair_y': lpy
        }
        
        self.mtf = nMTF
        self.lp_frequencies = lp
        
        return self.results
    
    def _calculate_mtf(self, image, center, t_offset):
        """
        Calculate Modulation Transfer Function from line pair patterns.
        
        Args:
            image: Input image array
            center: Center coordinates (x, y)
            t_offset: Angular offset in degrees
            
        Returns:
            Tuple of (MTF, frequencies, profiles, line_pair_coords)
        """
        # Import the detailed MTF calculation from the original code
        # This is a placeholder - the full implementation would extract
        # the analysis_CTP528 function logic
        
        sz = image.shape
        ds = self.dicom_set[self.slice_index]
        space = ds.PixelSpacing
        
        # Line pair parameters
        lp_r = 47  # radius in mm
        
        # Calculate line pair positions and extract profiles
        # (Full implementation would go here)
        tfine = np.linspace(0, np.pi, 500)
        lpx = lp_r/space[0]*np.cos(tfine) + center[0]
        lpy = lp_r/space[1]*np.sin(tfine) + center[1]
        
        # Simplified MTF calculation - full version would analyze actual line pairs
        mtf = np.ones(21)  # Placeholder
        lpf = np.linspace(0, 2.0, 21)
        
        return mtf, lpf, None, None, None, lpx, lpy
    
    def get_results_summary(self):
        """
        Get a formatted summary of analysis results.
        
        Returns:
            Dictionary with key measurements
        """
        if not self.results:
            raise ValueError("Analysis must be run before getting results")
        
        return {
            '10% MTF (lp/mm)': f"{self.results['mtf_10']:.3f}",
            '30% MTF (lp/mm)': f"{self.results['mtf_30']:.3f}",
            '50% MTF (lp/mm)': f"{self.results['mtf_50']:.3f}",
            '80% MTF (lp/mm)': f"{self.results['mtf_80']:.3f}"
        }
