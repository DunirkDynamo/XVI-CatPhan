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
        
        This is a wrapper that calls the utility function in CatPhanGeometry.
        
        Args:
            search_range: Number of slices to check above/below the target slice (unused, kept for compatibility)
            
        Returns:
            Tuple of (averaged_image, means_array, z_offset)
        """
        from ..utils.geometry import CatPhanGeometry
        
        im, means, z_mean = CatPhanGeometry.select_optimal_ctp528_slices(
            self.dicom_set, self.slice_index
        )
        
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
        
        mtf, profiles, _, _, _, lpx, lpy = self._calculate_mtf(
            self.averaged_image, 
            self.center, 
            self.rotation_offset
        )
        
        # Store profiles for plotting
        self.line_pair_profiles = profiles
        
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
        
        Full implementation from analysis_CTP528 in original processDICOMcat.py
        
        Args:
            image: Input image array
            center: Center coordinates (x, y)
            t_offset: Angular offset in degrees
            
        Returns:
            Tuple of (MTF, frequencies, profiles, lpx, lpy)
        """
        ds    = self.dicom_set[self.slice_index]
        sz    = (ds.Rows, ds.Columns)
        space = ds.PixelSpacing
        
        # x,y coordinates of image (in pixels)
        x = np.linspace(0, (sz[0]-1), sz[0])
        y = np.linspace(0, (sz[1]-1), sz[1])
        
        # Line pair parameters
        lp_r = 48  # radius in mm
        
        # Angles between line pairs
        theta = [
            np.radians(10 + t_offset),
            np.radians(40 + t_offset),
            np.radians(62 + t_offset),
            np.radians(85 + t_offset),
            np.radians(103 + t_offset),
            np.radians(121 + t_offset),
            np.radians(140 + t_offset),
            np.radians(157 + t_offset),
            np.radians(173 + t_offset),
            np.radians(186 + t_offset)
        ]
        
        lpx = lp_r/space[0]*np.cos(theta) + center[0]
        lpy = lp_r/space[0]*np.sin(theta) + center[1]
        
        # Number of peaks expected in each line pair
        npeaks = [[1,2],[2,3],[3,4],[4,4],[5,4],[6,5],[7,5],[8,5],[9,5],[10,5]]
        
        def get_MTF_single_pair(lpx_pair, lpy_pair, npeaks_pair):
            """Calculate MTF for a single line pair."""
            # Interpolate profile across line pair
            x1 = np.linspace(lpx_pair[0], lpx_pair[1], 50)
            y1 = np.linspace(lpy_pair[0], lpy_pair[1], 50)
            f1 = np.zeros(len(x1))
            
            for i in range(len(x1)):
                f1[i] = interpn((x, y), image, [y1[i], x1[i]])
            
            # Derivative of profile
            df1 = np.diff(f1)
            
            # Find inflection points (peaks in derivative)
            h = 50
            peaks_max1, _ = find_peaks(df1, height=h)
            peaks_min1, _ = find_peaks(-df1, height=h)
            
            # Reduce threshold until we find enough peaks
            while (len(peaks_max1) < npeaks_pair[1]) or (len(peaks_min1) < npeaks_pair[1]):
                if h <= 10:
                    # Cannot resolve this line pair
                    return 0, f1
                h -= 1
                peaks_max1, _ = find_peaks(df1, height=h)
                peaks_min1, _ = find_peaks(-df1, height=h)
            
            # Combine and sort peaks
            peaks1 = np.hstack((peaks_max1, peaks_min1))
            peaks1 = np.array(sorted(peaks1))
            
            # Find maxima and minima in the profile at peak locations
            idxmax = []
            idxmin = []
            Imax = []
            Imin = []
            offset = 1
            
            for i in range(len(peaks1)-1):
                if i % 2 == 0:
                    tmp = np.array(f1[peaks1[i]-offset:peaks1[i+1]+offset]).argmax()
                    idxmax.append(tmp - offset + peaks1[i])
                    Imax.append(f1[tmp - offset + peaks1[i]])
                else:
                    tmp = np.array(f1[peaks1[i]-offset:peaks1[i+1]+offset]).argmin()
                    idxmin.append(tmp - offset + peaks1[i])
                    Imin.append(f1[tmp - offset + peaks1[i]])
            
            # Calculate MTF for this line pair
            if len(Imax) > 0 and len(Imin) > 0:
                MTF = (np.mean(Imax) - np.mean(Imin)) / (np.mean(Imax) + np.mean(Imin))
            else:
                MTF = 0
                
            return MTF, f1
        
        # Calculate MTF for each line pair
        MTF = []
        profiles = []
        for i in range(len(theta)-1):
            mtf_val, profile = get_MTF_single_pair(
                (lpx[i], lpx[i+1]),
                (lpy[i], lpy[i+1]),
                npeaks[i]
            )
            MTF.append(mtf_val)
            profiles.append(profile)
        
        # Normalize MTF
        MTF = np.array(MTF)
        
        return MTF, profiles, None, None, None, lpx, lpy
    
    def get_plot_data(self):
        """
        Get data needed for plotting visualizations.
        
        Returns:
            Dictionary with plot data including line pair coordinates,
            outer boundary, and MTF curve data
        """
        from ..utils.geometry import CatPhanGeometry
        
        if not self.results:
            raise ValueError("Analysis must be run before getting plot data")
        
        # Get outer boundary for phantom visualization
        geometry = CatPhanGeometry()
        _, outer_boundary = geometry.find_center(self.averaged_image)
        
        return {
            'lpx': self.results['line_pair_x'],
            'lpy': self.results['line_pair_y'],
            'outer_boundary': outer_boundary,
            'mtf_data': {
                'nMTF': self.results['mtf_array'],
                'lp': self.results['lp_frequencies']
            },
            'line_pair_profiles': self.line_pair_profiles if hasattr(self, 'line_pair_profiles') else None
        }
    
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
