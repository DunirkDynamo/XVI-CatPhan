"""
Geometry utilities for CatPhan phantom analysis.

Provides functions for finding phantom centers, rotations, and geometric measurements.
"""

import numpy as np
from scipy.interpolate import interpn
from scipy.signal import find_peaks, peak_widths


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
        # `sz` stores the image shape as a NumPy array for simple arithmetic.
        sz = np.array(image.shape)

        # `matrix_c` is the approximate image midpoint used to sample central profiles.
        matrix_c = (np.round(sz[0]/2), np.round(sz[1]/2))
        
        # Extract orthogonal intensity profiles through the approximate phantom center.
        px = image[int(matrix_c[0]), :]
        py = image[:, int(matrix_c[1])]
        
        # `offset` nudges the detected edges slightly inward to stabilize the estimate.
        offset = 1
        
        try:
            # Find the first and last pixels above threshold along each center profile.
            x1 = next(x for x, val in enumerate(px) if val > threshold) + offset
            y1 = next(x for x, val in enumerate(py) if val > threshold) - offset
            x2 = next(x for x, val in reversed(list(enumerate(px))) if val > threshold) + offset
            y2 = next(x for x, val in reversed(list(enumerate(py))) if val > threshold) - offset
        except:
            # Retry with a lower threshold when the default edge search is too strict.
            threshold = 300
            x1 = next(x for x, val in enumerate(px) if val > threshold) + offset
            y1 = next(x for x, val in enumerate(py) if val > threshold) - offset
            x2 = next(x for x, val in reversed(list(enumerate(px))) if val > threshold) + offset
            y2 = next(x for x, val in reversed(list(enumerate(py))) if val > threshold) - offset
        
        # `szx` and `szy` are the detected phantom diameters in the two sampled directions.
        szx = x2 - x1
        szy = y2 - y1
        
        # `center` is the midpoint between the detected opposing phantom edges.
        center = [(x1 + x2) / 2, (y1 + y2) / 2]

        # `outer_r` is the average radius inferred from the two diameter estimates.
        outer_r = (szx + szy) / 4
        
        # Generate a circular outline that can be overlaid in diagnostic plots.
        t = np.linspace(0, 2*np.pi, 100)
        outer_x = outer_r * np.cos(t) + center[0]
        outer_y = outer_r * np.sin(t) + center[1]
        
        return center, [outer_x, outer_y]
    
    # Note: rotation detection is provided by the centralized Alexandria
    # implementation (`alexandria.utils.find_rotation`). Call that utility
    # directly or use the `CTP404Analyzer.detect_rotation()` workflow.
    
    @staticmethod
    def find_slice_ctp528(dicom_set, expected_slice=60):
        """
        Find the slice containing the CTP528 line pair module.
        
        Searches for the characteristic line pair pattern by analyzing
        profiles through the line pair regions and counting edge transitions.
        
        Args:
            dicom_set: List of DICOM datasets
            expected_slice: Expected slice index to start search
            
        Returns:
            Index of the CTP528 slice
        """
        def get_lp_profile(x, y, lpx, lpy, img):
            """Get profile across line pair region."""
            # `x1` is the evenly sampled x-coordinate path across one line-pair sector.
            x1 = np.linspace(lpx[0], lpx[1], 50)

            # `y1` is the evenly sampled y-coordinate path across one line-pair sector.
            y1 = np.linspace(lpy[0], lpy[1], 50)

            # `f1` will store the interpolated profile values across the sampled path.
            f1 = np.zeros(len(x1))
            
            # Interpolate the image intensity at each point along the path.
            for i in range(len(x1)):
                f1[i] = interpn((x, y), img, [y1[i], x1[i]])
            
            # `df1` is the first derivative used to count line-pair edge transitions.
            df1 = np.diff(f1)
            return f1, df1
        
        # Use an early slice to establish image size and pixel spacing information.
        idx_tmp = min(10, len(dicom_set) - 1)
        sz = (dicom_set[idx_tmp].Rows, dicom_set[idx_tmp].Columns)
        space = dicom_set[idx_tmp].PixelSpacing
        
        # `z_tmp` is the initial guess for the CTP528 module location.
        z_tmp = min(expected_slice, len(dicom_set) - 1)
        
        # Estimate the phantom center on the initial search slice.
        outer_c, _ = CatPhanGeometry.find_center(dicom_set[z_tmp].pixel_array)
        
        # Build the image coordinate axes in pixel units for interpolation.
        x = np.linspace(0, (sz[0]-1), sz[0])
        y = np.linspace(0, (sz[1]-1), sz[1])
        
        # `lp_r` is the radial distance from center to the line-pair sampling arc.
        lp_r = 48  # radius in pixels
        
        # `theta` contains the angular sampling positions spanning the line-pair sectors.
        theta = [np.radians(10), np.radians(38), np.radians(62), np.radians(85),
                 np.radians(103), np.radians(121), np.radians(140), np.radians(157),
                 np.radians(173), np.radians(186)]
        
        # `lpx` and `lpy` are the sampling coordinates for the line-pair arc endpoints.
        lpx = lp_r/space[0]*np.cos(theta) + outer_c[0]
        lpy = lp_r/space[0]*np.sin(theta) + outer_c[1]
        
        # Thresholds tuned to identify the characteristic number of derivative transitions.
        thres1 = 100  # Derivative threshold
        thres2 = 50   # Count threshold
        
        # Search the expected neighborhood first before falling back to the whole volume.
        search_order = [z_tmp, z_tmp+1, z_tmp-1, z_tmp+2, z_tmp-2]
        
        print('Searching for CTP528 module starting at expected slices')
        for i in search_order:
            if i < 0 or i >= len(dicom_set) - 1:
                continue
                
            print(f'Slice {i+1}')
            
            # Accumulate derivative responses across all line-pair sectors on this slice.
            tmpdf2 = np.array([])
            for j in range(len(theta)-1):
                _, tmpdf = get_lp_profile(x, y, (lpx[j], lpx[j+1]), 
                                         (lpy[j], lpy[j+1]), 
                                         dicom_set[i].pixel_array)
                tmpdf2 = np.hstack((tmpdf2, tmpdf)) if tmpdf2.size else tmpdf
            
            # Accept the slice once the derivative response matches the expected signature.
            if np.sum(abs(tmpdf2) > thres1) > thres2:
                print(f'CTP528 module located: Slice {i+1}')
                return i
        
        # Fall back to a full-volume search when the local neighborhood search fails.
        print('--- Parsing through each slice to find module CTP528 ---')
        for i in range(len(dicom_set) - 1):
            print(f'Slice {i+1}')
            
            tmpdf2 = np.array([])
            for j in range(len(theta)-1):
                try:
                    _, tmpdf = get_lp_profile(x, y, (lpx[j], lpx[j+1]), 
                                             (lpy[j], lpy[j+1]), 
                                             dicom_set[i].pixel_array)
                    tmpdf2 = np.hstack((tmpdf2, tmpdf)) if tmpdf2.size else tmpdf
                except:
                    continue
            
            if np.sum(abs(tmpdf2) > thres1) > thres2:
                print(f'CTP528 module located: Slice {i+1}')
                return i
        
        print('Error: Cannot locate CTP528 module')
        return z_tmp  # Return expected slice as fallback
    
    @staticmethod
    def calculate_slice_thickness(image, pixel_spacing, center):
        """
        Calculate slice thickness using wire ramp.
        
        Full implementation from FindSliceThickness in original processDICOMcat.py
        
        Args:
            image: 2D numpy array of the image
            pixel_spacing: Pixel spacing in mm [row_spacing, col_spacing]
            center: Center coordinates (x, y)
            
        Returns:
            Slice thickness in mm
        """
        # `c` is the integer pixel-space center used for array indexing.
        c = np.int32(center)
        
        # Define the wire-ramp ROI bounds relative to the module center.
        roit = 80
        roib = 70
        roil = -30
        roir = 30
        
        # `profs` is the wire-ramp subimage used to estimate the slice thickness.
        profs    = image[c[1]+roil:c[1]+roir, c[0]+roib:c[0]+roit]

        # `idx_prof` identifies the brightest wire profile column inside the ROI.
        idx_prof = np.argmax(np.sum(profs, axis=0))
        
        # `h` is the half-height threshold used to locate the wire peak.
        h        = (np.max(profs) + np.min(profs)) / 2
        peaks, _ = find_peaks(profs[:, idx_prof], height=h)
        
        # Convert the wire-profile full width at half maximum into slice thickness.
        peaks_results = peak_widths(profs[:, idx_prof], peaks, rel_height=0.5)
        FWHM          = peaks_results[0] * np.sin(np.deg2rad(23)) * pixel_spacing[0]
        
        return FWHM[0] if len(FWHM) > 0 else 5.0

    @staticmethod
    def select_optimal_ctp528_slices(dicom_set, slice_index):
        """
        Select and average 3 slices around the CTP528 module for optimal contrast.
        
        Analyzes 5 slices (z-2 to z+2) and finds the 3 consecutive slices
        with highest intensity through the line pairs.
        
        Args:
            dicom_set: List of DICOM datasets
            slice_index: Index of the initially found CTP528 slice
            
        Returns:
            Tuple of (averaged_image, means_array, z_offset)
        """
        # `z` is the nominal CTP528 slice index passed in by the locator.
        z  = slice_index

        # `ds` is a short alias for the ordered DICOM dataset list.
        ds = dicom_set
        
        # Extract the five-slice neighborhood around the target module location.
        img_zm2 = ds[z-2].pixel_array
        img_zm1 = ds[z-1].pixel_array
        img_z = ds[z].pixel_array
        img_zp1 = ds[z+1].pixel_array
        img_zp2 = ds[z+2].pixel_array
        
        # `sz`, `space`, and `c` define the image dimensions, spacing, and midpoint.
        sz = (ds[z].Rows, ds[z].Columns)
        space = ds[z].PixelSpacing
        c = (int(sz[0]/2), int(sz[1]/2))
        
        # Build a fine sampling arc that passes through the line-pair region.
        lp_r = 47  # radius in mm
        tfine = np.linspace(0, np.pi, 500)
        lp_b = lp_r/space[0]*np.cos(tfine) + c[0]
        lp_a = lp_r/space[1]*np.sin(tfine) + c[1]
        
        # Build interpolation axes for the native image grid.
        x = np.linspace(0, (sz[0]-1)/2, sz[0])
        y = np.linspace(0, (sz[1]-1)/2, sz[1])
        
        # Collect the five neighboring images and prepare to sample each one along the arc.
        images = [img_zm2, img_zm1, img_z, img_zp1, img_zp2]
        profiles = []
        
        # Sample each candidate slice along the line-pair arc.
        for im in images:
            # `f` is the sampled intensity profile for the current candidate slice.
            f = np.zeros(len(lp_a))
            for i in range(len(lp_a)):
                f[i] = interpn((x, y), im, [lp_a[i]*space[0], lp_b[i]*space[1]])
            profiles.append(f)
        
        # `means` stores the average profile intensity for each candidate slice.
        means = [np.mean(f) for f in profiles]

        # `tmp` is the index of the candidate slice with the strongest average signal.
        tmp   = np.argmax(means)
        
        # Mark the three-slice window centered on the strongest candidate when possible.
        idx = np.zeros(5)
        try:
            idx[tmp-1] = 1
            idx[tmp] = 1
            idx[tmp+1] = 1
        except:
            # Handle edge cases where the best candidate lies at the edge of the search window.
            if tmp == 0:
                idx = [1, 1, 0, 0, 0]
            elif tmp == 4:
                idx = [0, 0, 0, 1, 1]
            else:
                return img_z, means, 0
        
        # Accumulate the selected slices and record their offsets from the center slice.
        im = np.zeros(sz)
        z_mean = []
        
        for i, include in enumerate(idx):
            if include:
                im += images[i]
                z_mean.append(i - 2)
        
        # Normalize the summed image and compute the mean slice offset that was selected.
        im = im / sum(idx)
        z_mean = np.mean(z_mean)
        
        return im, means, z_mean


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
        # Store the sorted series that will be searched for module locations.
        self.dicom_set = dicom_set

        # Hold the discovered slice indices for each CatPhan module.
        self.ctp528_index = None
        self.ctp404_index = None
        self.ctp486_index = None
        
    def locate_all_modules(self):
        """
        Locate all three CatPhan modules.
        
        Returns:
            Dictionary with slice indices for each module and z_mean offset
        """
        # Locate the CTP528 module first because the other modules are positioned relative to it.
        self.ctp528_index = CatPhanGeometry.find_slice_ctp528(self.dicom_set)
        
        # Use the optimal CTP528 averaging window to refine the effective axial position.
        _, _, z_mean = CatPhanGeometry.select_optimal_ctp528_slices(self.dicom_set, self.ctp528_index)
        
        # Distances from CTP528 to the other modules for the CatPhan-500 geometry.
        d_CTP404 = 30   # mm from CTP528
        d_CTP486 = -80  # mm from CTP528
        
        # Extract slice-thickness and neighboring slice-location metadata.
        z = self.dicom_set[self.ctp528_index].SliceThickness
        z1 = self.dicom_set[self.ctp528_index].SliceLocation
        z2 = self.dicom_set[self.ctp528_index + 1].SliceLocation
        
        # Account for scan direction so the relative module offsets are applied correctly.
        if (z2 - z1) > 0:
            # Increasing slice locations indicate one axial ordering convention.
            self.ctp404_index = int(self.ctp528_index + z_mean + float(d_CTP404) / z)
            self.ctp486_index = int(self.ctp528_index + z_mean + float(d_CTP486) / z)
        else:
            # Decreasing slice locations indicate the opposite axial ordering convention.
            self.ctp404_index = int(self.ctp528_index + z_mean - float(d_CTP404) / z)
            self.ctp486_index = int(self.ctp528_index + z_mean - float(d_CTP486) / z)
        
        return {
            'ctp528': self.ctp528_index,
            'ctp404': self.ctp404_index,
            'ctp486': self.ctp486_index
        }
