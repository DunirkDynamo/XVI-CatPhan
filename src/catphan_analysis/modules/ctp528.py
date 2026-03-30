"""
CTP528 Module - Line Pair Resolution Analysis

This module handles the analysis of the CTP528 high-resolution module,
including MTF calculation and line pair resolution measurement.
"""

import numpy as np
from scipy.interpolate import interpn
from scipy.signal import find_peaks


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
        # Store the dataset and geometry metadata needed for resolution analysis.
        self.dicom_set = dicom_set
        self.slice_index = slice_index
        self.center = center
        self.rotation_offset = rotation_offset

        # Cache the averaged image and derived MTF outputs for later plotting/reporting.
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
        
        # Delegate the slice-selection logic to the shared geometry helper.
        im, means, z_mean = CatPhanGeometry.select_optimal_ctp528_slices(
            self.dicom_set, self.slice_index
        )
        
        # Cache the averaged image so later analysis steps do not repeat the selection.
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
        
        # Calculate the raw MTF curve and line-pair sampling coordinates from the averaged image.
        mtf, profiles, _, _, _, lpx, lpy = self._calculate_mtf(
            self.averaged_image, 
            self.center, 
            self.rotation_offset
        )
        
        # Preserve the individual line-pair profiles for diagnostic plotting.
        self.line_pair_profiles = profiles
        
        # Normalize the MTF curve so the highest response equals 1.0.
        nMTF = mtf / max(np.array(mtf))
        
        # Build the nominal line-pair frequency axis and interpolate standard reporting points.
        lp = np.linspace(1, len(mtf), len(mtf)) / 10
        MTF_sample = (0.8, 0.5, 0.3, 0.1)
        fMTF = np.interp(MTF_sample, nMTF[::-1], lp[::-1])
        
        # Persist the standard reported MTF values and supporting arrays.
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
        
        # Store the normalized MTF and frequency axis for summary and plotting helpers.
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
        # `ds` is the DICOM dataset for the selected CTP528 slice.
        ds    = self.dicom_set[self.slice_index]

        # `sz` and `space` describe the image geometry in pixels and millimeters.
        sz    = (ds.Rows, ds.Columns)
        space = ds.PixelSpacing
        
        # Build the image-grid axes used for interpolation.
        x = np.linspace(0, (sz[0]-1), sz[0])
        y = np.linspace(0, (sz[1]-1), sz[1])
        
        # `lp_r` is the radial distance from the phantom center to the line-pair sectors.
        lp_r = 48  # radius in mm
        
        # `theta` contains the angular boundaries of the line-pair sectors after rotation correction.
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
        
        # `lpx` and `lpy` are the sampling coordinates along the line-pair arc.
        lpx = lp_r/space[0]*np.cos(theta) + center[0]
        lpy = lp_r/space[0]*np.sin(theta) + center[1]
        
        # `npeaks` encodes the expected number of derivative peaks for each line-pair band.
        npeaks = [[1,2],[2,3],[3,4],[4,4],[5,4],[6,5],[7,5],[8,5],[9,5],[10,5]]
        
        def get_MTF_single_pair(lpx_pair, lpy_pair, npeaks_pair):
            """Calculate MTF for a single line pair."""
            # Sample a profile across the current line-pair sector.
            x1 = np.linspace(lpx_pair[0], lpx_pair[1], 50)
            y1 = np.linspace(lpy_pair[0], lpy_pair[1], 50)
            f1 = np.zeros(len(x1))
            
            # Interpolate the image intensity at each sampled profile point.
            for i in range(len(x1)):
                f1[i] = interpn((x, y), image, [y1[i], x1[i]])
            
            # Differentiate the profile so bar-pattern transitions become peaks.
            df1 = np.diff(f1)
            
            # Start with a conservative derivative threshold for peak detection.
            h = 50
            peaks_max1, _ = find_peaks(df1, height=h)
            peaks_min1, _ = find_peaks(-df1, height=h)
            
            # Relax the threshold until enough maxima/minima are resolved.
            while (len(peaks_max1) < npeaks_pair[1]) or (len(peaks_min1) < npeaks_pair[1]):
                if h <= 10:
                    # Return zero response when the line pair cannot be reliably resolved.
                    return 0, f1
                h -= 1
                peaks_max1, _ = find_peaks(df1, height=h)
                peaks_min1, _ = find_peaks(-df1, height=h)
            
            # Merge positive and negative derivative peaks into a single ordered sequence.
            peaks1 = np.hstack((peaks_max1, peaks_min1))
            peaks1 = np.array(sorted(peaks1))
            
            # Identify the local maxima and minima in the original profile between derivative peaks.
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
            
            # Compute the modulation ratio for the current line-pair sector.
            if len(Imax) > 0 and len(Imin) > 0:
                MTF = (np.mean(Imax) - np.mean(Imin)) / (np.mean(Imax) + np.mean(Imin))
            else:
                MTF = 0
                
            return MTF, f1
        
        # Evaluate the modulation response for each line-pair sector in turn.
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
        
        # Convert the list of modulation values into a NumPy array for downstream math.
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
        
        # Recompute the phantom boundary so the module outline can be overlaid in plots.
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
        
        # Return the standard MTF reporting values as formatted strings.
        return {
            '10% MTF (lp/mm)': f"{self.results['mtf_10']:.3f}",
            '30% MTF (lp/mm)': f"{self.results['mtf_30']:.3f}",
            '50% MTF (lp/mm)': f"{self.results['mtf_50']:.3f}",
            '80% MTF (lp/mm)': f"{self.results['mtf_80']:.3f}"
        }
