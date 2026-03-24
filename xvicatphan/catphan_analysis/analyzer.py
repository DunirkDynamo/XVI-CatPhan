"""
CatPhan Analyzer - Executive Class

Main class that coordinates all CatPhan phantom analysis modules.
"""

import os
import sys
from pathlib import Path
import numpy as np
import pydicom as dicom
import matplotlib.pyplot as plt
import datetime
from typing import Dict, List, Optional
import warnings

# Import Alexandria analyzers
from alexandria import CTP404Analyzer, UniformityAnalyzer, HighContrastAnalyzer, DetailedUniformityAnalyzer
from alexandria.plotters import CTP404Plotter, HighContrastPlotter, UniformityPlotter, DetailedUniformityPlotter
from .utils.geometry import CatPhanGeometry, SliceLocator
from .utils.image_processing import ImageProcessor


class CatPhanAnalyzer:
    """
    Executive class for coordinating CatPhan phantom analysis.
    
    This class initializes and manages all analysis module classes,
    coordinates the analysis workflow, and generates reports.
    """
    
    def __init__(self, dicom_path, output_path=None, catphan_model='500',
                 center_threshold: float = 400,
                 center_threshold_fallback: float = 300):
        """
        Initialize the CatPhan analyzer.
        
        Args:
            dicom_path: Path to directory containing DICOM files
            output_path: Path for output files (default: same as dicom_path)
            catphan_model: CatPhan model ('500' or '504')
        """
        self.dicom_path    = Path(dicom_path)
        self.output_path   = Path(output_path) if output_path else self.dicom_path
        self.catphan_model = catphan_model
        # Thresholds used by analyzers that detect center/boundary
        self.center_threshold = float(center_threshold)
        self.center_threshold_fallback = float(center_threshold_fallback)
        
        # Data storage
        self.dicom_set       = []
        self.slice_indices   = {}
        self.module_centers  = {}
        self.rotation_offset = 0.0
        
        # Analysis modules (initialized later)
        self.ctp404          = None
        self.ctp486          = None
        self.ctp528          = None
        self.ctp486_detailed = None
        
        # Rotation points for CTP404
        self.ct_point = None
        self.cb_point = None
        
        # Results
        self.results = {}
        
        # Log file
        self.log_file = None
        
    def load_dicom_files(self):
        """
        Load and sort DICOM files from the input directory.
        
        Returns:
            Number of files loaded
        """
        self._log("Loading DICOM files...")
        
        dicom_pairs = []
        missing_slice_location = 0
        
        for root, _, filenames in os.walk(self.dicom_path):
            for filename in filenames:
                # Skip non-DICOM files
                if 'dir' in filename or 'txt' in filename:
                    continue
                
                dcm_path = Path(root, filename)
                
                try:
                    ds = dicom.dcmread(dcm_path, force=True)
                    ds.file_meta.TransferSyntaxUID = dicom.uid.ImplicitVRLittleEndian

                    sort_value = None
                    if hasattr(ds, "SliceLocation"):
                        sort_value = float(ds.SliceLocation)
                    elif hasattr(ds, "ImagePositionPatient") and len(ds.ImagePositionPatient) >= 3:
                        sort_value = float(ds.ImagePositionPatient[2])
                    elif hasattr(ds, "InstanceNumber"):
                        sort_value = float(ds.InstanceNumber)

                    if sort_value is None:
                        missing_slice_location += 1
                        sort_value = float(len(dicom_pairs))

                    dicom_pairs.append((sort_value, ds))
                except Exception as e:
                    self._log(f"Can't import {dcm_path.stem}: {e}")
        
        if missing_slice_location > 0:
            self._log(
                f"Warning: {missing_slice_location} file(s) missing SliceLocation; "
                "used ImagePositionPatient/InstanceNumber for ordering."
            )
        
        # Sort by inferred slice position
        dicom_pairs.sort(key=lambda item: item[0], reverse=True)
        self.dicom_set = [ds for _, ds in dicom_pairs]
        
        self._log(f"Loaded {len(self.dicom_set)} DICOM files")
        
        if len(self.dicom_set) > 0:
            self._log(f"Unit: {self.dicom_set[0].StationName}")
        
        return len(self.dicom_set)
    
    def locate_modules(self):
        """
        Locate the three CatPhan modules in the DICOM series.
        
        Returns:
            Dictionary with slice indices for each module
        """
        self._log("\n--- Locating CatPhan modules ---")
        
        locator = SliceLocator(self.dicom_set)
        self.slice_indices = locator.locate_all_modules()
        
        self._log(f"CTP528 (Line Pairs) found at slice: {self.slice_indices['ctp528']}")
        self._log(f"CTP404 (Contrast) found at slice: {self.slice_indices['ctp404']}")
        self._log(f"CTP486 (Uniformity) found at slice: {self.slice_indices['ctp486']}")
        
        return self.slice_indices
    
    def find_module_centers(self):
        """
        Find the center of each module to correct for setup errors.
        
        Returns:
            Dictionary with center coordinates for each module
        """
        self._log("\n--- Finding module centers ---")
        
        geometry = CatPhanGeometry()
        
        # Get initial images for each module
        idx_528 = self.slice_indices['ctp528']
        idx_404 = self.slice_indices['ctp404']
        idx_486 = self.slice_indices['ctp486']
        
        # For CTP528, use intelligent slice selection (same as original image_selector_CTP528)
        im_528, _, _ = geometry.select_optimal_ctp528_slices(self.dicom_set, idx_528)
        
        # For CTP404 and CTP486, use simple 3-slice averaging
        im_404 = ImageProcessor.average_slices(self.dicom_set, [idx_404-1, idx_404, idx_404+1])
        im_486 = ImageProcessor.average_slices(self.dicom_set, [idx_486-1, idx_486, idx_486+1])
        
        # Find centers
        c_528, _ = geometry.find_center(im_528)
        c_404, _ = geometry.find_center(im_404)
        c_486, _ = geometry.find_center(im_486)
        
        self.module_centers = {
            'ctp528': c_528,
            'ctp404': c_404,
            'ctp486': c_486
        }
        
        self._log(f"CTP528 center: ({c_528[0]:.1f}, {c_528[1]:.1f})")
        self._log(f"CTP404 center: ({c_404[0]:.1f}, {c_404[1]:.1f})")
        self._log(f"CTP486 center: ({c_486[0]:.1f}, {c_486[1]:.1f})")
        
        return self.module_centers
    
    def find_rotation(self):
        """
        Find the rotation of the CatPhan phantom.
        
        Returns:
            Rotation angle in degrees
        """
        self._log("\n--- Finding CatPhan rotation ---")
        
        geometry = CatPhanGeometry()
        idx_404 = self.slice_indices['ctp404']
        im_404 = self.dicom_set[idx_404].pixel_array
        c_404 = self.module_centers['ctp404']
        space = self.dicom_set[idx_404].PixelSpacing
        # Rotation detection is now handled by the CTP404 analyzer's
        # `detect_rotation()` implementation. Use `run_ctp404()` or
        # `analyze()` to perform rotation detection and related refinements.
        raise AttributeError("CatPhanAnalyzer.find_rotation() has been removed; use run_ctp404() or analyzer.ctp404.detect_rotation()")
    
    def initialize_modules(self):
        """
        Initialize all analysis module classes.
        """
        self._log("\n--- Initializing analysis modules ---")
        
        # CTP404 - Contrast module (using Alexandria)
        self.ctp404 = CTP404Analyzer(
            dicom_set=self.dicom_set,
            slice_index=self.slice_indices['ctp404'],
            center=self.module_centers['ctp404'],
            rotation_offset=self.rotation_offset
        )
        
        # CTP486 - Uniformity module (using Alexandria)
        self.ctp486 = UniformityAnalyzer(
            dicom_set=self.dicom_set,
            slice_index=self.slice_indices['ctp486'],
            center=self.module_centers['ctp486']
        )

        # CTP486 - Detailed uniformity (using Alexandria)
        self.ctp486_detailed = DetailedUniformityAnalyzer(
            dicom_set=self.dicom_set,
            slice_index=self.slice_indices['ctp486'],
            center=self.module_centers['ctp486']
        )
        
        # CTP528 - Resolution module (using Alexandria)
        self.ctp528 = HighContrastAnalyzer(
            dicom_set=self.dicom_set,
            slice_index=self.slice_indices['ctp528'],
            center=self.module_centers['ctp528'],
            center_threshold=self.center_threshold,
            center_threshold_fallback=self.center_threshold_fallback
            # Note: HighContrastAnalyzer handles line pair detection automatically
        )
        
        self._log("All modules initialized successfully")

    def run_ctp404(self, verbose: bool = False) -> Dict:
        """
        Run the CTP404 analyzer end-to-end:
        - ensure analyzer exists
        - run its `detect_rotation()` to set `self.rotation_offset` and rotation points
        - compute spatial-scaling refinement (refine center) and re-init analyzer if needed
        - run `analyze()` and normalize results
        """
        # Ensure analyzer instance
        if self.ctp404 is None:
            self.ctp404 = CTP404Analyzer(
                dicom_set=self.dicom_set,
                slice_index=self.slice_indices['ctp404'],
                center=self.module_centers['ctp404'],
                rotation_offset=self.rotation_offset
            )

        # Let analyzer find rotation (overrides external geometry finder)
        try:
            rot_res = self.ctp404.detect_rotation()
            if isinstance(rot_res, tuple) and len(rot_res) == 3:
                rotation_angle, top_pt, bottom_pt = rot_res
            else:
                rotation_angle = float(rot_res)
                top_pt = getattr(self.ctp404, 'rotation_top_point', None)
                bottom_pt = getattr(self.ctp404, 'rotation_bottom_point', None)
        except Exception:
            # Fallback: retain any existing rotation_offset
            rotation_angle = self.rotation_offset
            top_pt = getattr(self, 'ct_point', None)
            bottom_pt = getattr(self, 'cb_point', None)

        self.rotation_offset = float(rotation_angle)
        self.ct_point = top_pt
        self.cb_point = bottom_pt

        # Spatial-scaling refinement using ct_point/cb_point (if available)
        x_scale = None
        y_scale = None
        if self.ct_point is not None and self.cb_point is not None:
            self._log("Calculating refined CTP404 center using spatial scaling...")
            x_scale, y_scale, pts = self._calculate_spatial_scaling(self.ct_point, self.cb_point)

            # Store scaling points for legacy plotting
            self.scaling_pts = pts

            refined_center = [np.mean([pts[0], pts[2]]), np.mean([pts[1], pts[3]])]
            self._log(f"Original CTP404 center: ({self.module_centers['ctp404'][0]:.1f}, {self.module_centers['ctp404'][1]:.1f})")
            self._log(f"Refined CTP404 center: ({refined_center[0]:.1f}, {refined_center[1]:.1f})")

            # Update center and reinitialize CTP404 module with refined center
            self.module_centers['ctp404'] = refined_center
            self.ctp404 = CTP404Analyzer(
                dicom_set=self.dicom_set,
                slice_index=self.slice_indices['ctp404'],
                center=refined_center,
                rotation_offset=self.rotation_offset
            )

        # Run analysis
        raw_results_404 = self.ctp404.analyze(verbose=verbose)
        results_404 = self._build_ctp404_results(raw_results_404)

        # Add scaling results if available
        if x_scale is not None and y_scale is not None:
            results_404['x_scale_cm'] = x_scale
            results_404['y_scale_cm'] = y_scale
            self._log(f"X Scale: {x_scale:.2f} cm")
            self._log(f"Y Scale: {y_scale:.2f} cm")
        else:
            results_404['x_scale_cm'] = float('nan')
            results_404['y_scale_cm'] = float('nan')

        return results_404

    def run_ctp486(self, verbose: bool = False) -> Dict:
        """Run the CTP486 uniformity analyzer and normalize results."""
        if self.ctp486 is None:
            self.ctp486 = UniformityAnalyzer(
                dicom_set=self.dicom_set,
                slice_index=self.slice_indices['ctp486'],
                center=self.module_centers['ctp486']
            )

        raw_results_486 = self.ctp486.analyze(verbose=verbose)
        results_486 = self._build_ctp486_results(raw_results_486)
        return results_486

    def run_ctp486_detailed(self, verbose: bool = False) -> Dict:
        """Run the detailed uniformity analyzer."""
        if self.ctp486_detailed is None:
            self.ctp486_detailed = DetailedUniformityAnalyzer(
                dicom_set=self.dicom_set,
                slice_index=self.slice_indices['ctp486'],
                center=self.module_centers['ctp486']
            )
        # DetailedUniformityAnalyzer.analyze() does not accept a `verbose`
        # keyword — call it without kwargs. Keep the `verbose` parameter
        # on this runner for API consistency.
        if verbose:
            self._log("Running detailed uniformity analysis (verbose mode)")
        return self.ctp486_detailed.analyze()

    def run_ctp528(self, verbose: bool = False) -> Dict:
        """Run the CTP528 (high-contrast) analyzer."""
        if self.ctp528 is None:
            self.ctp528 = HighContrastAnalyzer(
                dicom_set=self.dicom_set,
                slice_index=self.slice_indices['ctp528'],
                center=self.module_centers['ctp528'],
                center_threshold=self.center_threshold,
                center_threshold_fallback=self.center_threshold_fallback
            )
        return self.ctp528.analyze(verbose=verbose)
    
    def analyze(self):
        """
        Run complete analysis of all modules.
        
        Returns:
            Dictionary with all results
        """
        if not self.dicom_set:
            self.load_dicom_files()

        if not self.slice_indices:
            self.locate_modules()

        if not self.module_centers:
            self.find_module_centers()

        # Initialize modules (creates analyzer instances)
        if not self.ctp404 or not self.ctp486 or not self.ctp486_detailed or not self.ctp528:
            self.initialize_modules()

        self._log("\n\n=== BEGINNING ANALYSIS ===\n")

        # Run modules via dedicated runners
        self._log("--- Analyzing CTP404 (Contrast/Scaling) ---")
        results_404 = self.run_ctp404(verbose=False)

        self._log("\n--- Analyzing CTP486 (Uniformity) ---")
        results_486 = self.run_ctp486(verbose=False)

        self._log("\n--- Analyzing CTP486 (Detailed Uniformity) ---")
        results_486_detailed = self.run_ctp486_detailed(verbose=False)

        self._log("\n--- Analyzing CTP528 (Resolution) ---")
        results_528 = self.run_ctp528(verbose=False)

        # Compile results
        self.results = {
            'ctp404': results_404,
            'ctp486': results_486,
            'ctp486_detailed': results_486_detailed,
            'ctp528': results_528,
            'metadata': {
                'unit': self.dicom_set[0].StationName,
                'study_date': self.dicom_set[0].StudyDate,
                'study_time': self.dicom_set[0].StudyTime
            }
        }

        self._log("\n=== ANALYSIS COMPLETE ===\n")

        # Produce legacy-style combined plot using already-run analyzers.
        try:
            self.generate_legacy_plots()
        except Exception as e:
            self._log(f"Legacy plotting skipped/error: {e}")

        return self.results
    
    def generate_report(self, include_plots=True):
        """
        Generate a text report and optional plots.
        
        Args:
            include_plots: Whether to generate plots
            
        Returns:
            Path to the report file
        """
        if not self.results:
            raise ValueError("Analysis must be run before generating report")
        
        self._log("\n--- Generating report ---")
        
        # Create report filename
        ds = self.dicom_set[0]
        date_str = f"{ds.StudyDate[0:4]}-{ds.StudyDate[4:6]}-{ds.StudyDate[6:8]}"
        time_str = f"{ds.StudyTime[0:2]}:{ds.StudyTime[2:4]}:{ds.StudyTime[4:6]}"
        unit_name = ds.StationName
        
        report_filename = f"CatPhan_{unit_name}_{date_str}.txt"
        report_path = self.output_path / report_filename
        
        # Write report
        with open(report_path, 'w') as f:
            f.write("CatPhan Analysis Script Results\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Date: {date_str}\n")
            f.write(f"Time: {time_str}\n")
            f.write(f"Unit: {unit_name}\n\n")
            
            # CTP404 Results
            f.write("----- Module 404 (Contrast Circles) -----\n")
            f.write("ROI,Material,Mean,STD\n")
            for roi_data in self.results['ctp404']['contrast_rois']:
                f.write(f"{roi_data[0]},{roi_data[1]},{roi_data[2]:.1f},{roi_data[3]:.1f}\n")
            
            f.write(f"\nLow contrast visibility: {self.results['ctp404']['low_contrast_visibility']:.3f} %\n")
            f.write(f"X Scale: {self.results['ctp404']['x_scale_cm']:.2f} cm\n")
            f.write(f"Y Scale: {self.results['ctp404']['y_scale_cm']:.2f} cm\n")
            f.write(f"Slice thickness: {self.results['ctp404']['slice_thickness_mm']:.2f} mm\n\n")
            
            # CTP486 Results
            f.write("----- Module 486 (Uniformity) -----\n")
            f.write("ROI,Mean,STD\n")
            for region_data in self.results['ctp486']['regions']:
                f.write(f"{region_data[0]},{region_data[1]:.1f},{region_data[2]:.1f}\n")
            f.write(f"Uniformity: {self.results['ctp486']['uniformity_percent']:.2f} %\n\n")
            
            # CTP528 Results
            f.write("----- Module 528 (Line Pairs) -----\n")
            f.write(f"10% MTF: {self.results['ctp528']['mtf_10']:.3f} lp/mm\n")
            f.write(f"30% MTF: {self.results['ctp528']['mtf_30']:.3f} lp/mm\n")
            f.write(f"50% MTF: {self.results['ctp528']['mtf_50']:.3f} lp/mm\n")
            f.write(f"80% MTF: {self.results['ctp528']['mtf_80']:.3f} lp/mm\n\n")
            
            # Misc Results
            f.write("----- Misc -----\n")
            f.write(f"Catphan rotation (deg): {self.rotation_offset:.1f}\n")
        
        self._log(f"Report saved: {report_path}")
        
        # Generate plots if requested
        if include_plots:
            plot_paths = self._generate_plots()
            if plot_paths:
                plot_list = ", ".join(str(path) for path in plot_paths)
                self._log(f"Plots saved: {plot_list}")
        
        return report_path
    
    def _generate_plots(self):
        """
        Generate visualization plots using Alexandria plotters.
        
        Returns:
            List of plot file paths
        """
        ds = self.dicom_set[0]
        date_str = f"{ds.StudyDate[0:4]}-{ds.StudyDate[4:6]}-{ds.StudyDate[6:8]}"
        unit_name = ds.StationName
        
        base_name = f"CatPhan_{unit_name}_{date_str}"
        plot_paths = []
        
        plotters = [
            ("CTP404"         , CTP404Plotter(self.ctp404)),
            ("CTP486"         , UniformityPlotter(self.ctp486)),
            ("CTP486_Detailed", DetailedUniformityPlotter(self.ctp486_detailed)),
            ("CTP528"         , HighContrastPlotter(self.ctp528)),
        ]
        
        for label, plotter in plotters:
            fig = plotter.plot()
            plot_path = self.output_path / f"{base_name}_{label}.png"
            # Try saving; if constrained_layout cannot be applied (axes collapsed),
            # fall back to disabling constrained_layout and using tight_layout().
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                try:
                    fig.savefig(plot_path, dpi=150, bbox_inches="tight")
                except Exception:
                    fig.set_constrained_layout(False)
                    fig.tight_layout()
                    fig.savefig(plot_path, dpi=150, bbox_inches="tight")
                else:
                    for warn in w:
                        if "constrained_layout not applied" in str(warn.message):
                            fig.set_constrained_layout(False)
                            fig.tight_layout()
                            fig.savefig(plot_path, dpi=150, bbox_inches="tight")
                            break
            plt.close(fig)
            plot_paths.append(plot_path)
        
        return plot_paths

    def generate_legacy_plots(self,
                              ):
        """
        Reproduce the legacy `processDICOMcat2.py` 2x2 plotting layout exactly.

        This method is a drop-in reproduction of the plotting block in
        `processDICOMcat2.py`. It does not attempt to compute any of the
        input images or derived data (MTF/Lp/ROI coordinates); callers must
        provide the same variables that the legacy script used so the
        visual output is identical.

        Args (positional, match legacy script names):
            mainpath: base path used to save the legacy plot (`mainpath + '\\CatPhan_results.png'`)
            im_CTP528: image array for CTP528
            out_CTP528: outer boundary points for CTP528 (iterable of x,y)
            lpx, lpy: line-pair overlay coordinates for CTP528
            im_CTP404: image array for CTP404
            ROI_CTP404: ROI polygon arrays for CTP404 (shape compatible with indexing used in legacy script)
            pts: scaling points (used to plot two green line points in legacy)
            im_CTP486: image array for CTP486
            out_CTP486: outer boundary points for CTP486 (iterable of x,y)
            ROI_CTP486: ROI bounding boxes for CTP486 (legacy format)
            lp: x-axis values for MTF plot
            nMTF: normalized MTF array
            nMTF80,nMTF50,nMTF30,nMTF10: numeric MTF markers
            Vmin,Vmax: image display vmin/vmax

        Returns:
            Path to saved PNG file (string)
        """
        # This analyzer-driven implementation pulls plotting inputs from
        # the already-run analyzer objects. It will not re-run analysis.
        if not (self.ctp528 and self.ctp404 and self.ctp486):
            raise ValueError("Analyzers must be initialized and run before plotting")

        # Prepare display window/level identical to legacy script
        fsize = 15
        window = 1000
        level = 1000
        Vmin = int(level - window / 2)
        Vmax = int(level + window / 2)

        # Gather CTP528 plot data
        ctp528 = self.ctp528
        try:
            p528 = ctp528.get_plot_data()
            im_CTP528 = p528.get('image', ctp528.image)
            lpx = p528.get('lpx', getattr(ctp528, 'lpx', None))
            lpy = p528.get('lpy', getattr(ctp528, 'lpy', None))
            mtf_data = p528.get('mtf_data', {})
            nMTF = mtf_data.get('nMTF', getattr(ctp528, 'nMTF', None))
            lp = mtf_data.get('lp', getattr(ctp528, 'lp_frequencies', None))
            mtf_points = p528.get('mtf_points', getattr(ctp528, 'mtf_points', {}))
            out_CTP528 = p528.get('outer_boundary', ([], []))
        except Exception:
            im_CTP528 = getattr(ctp528, 'image', None)
            lpx = getattr(ctp528, 'lpx', None)
            lpy = getattr(ctp528, 'lpy', None)
            nMTF = getattr(ctp528, 'nMTF', None)
            lp = getattr(ctp528, 'lp_frequencies', None)
            mtf_points = getattr(ctp528, 'mtf_points', {})
            out_CTP528 = getattr(ctp528, 'boundary', ([], []))

        # Log CTP528 boundary info for debugging
        try:
            if out_CTP528 is None:
                self._log('CTP528: no outer boundary found')
            else:
                try:
                    b_arr = np.array(out_CTP528)
                    self._log(f'CTP528 boundary shape: {b_arr.shape}')
                except Exception:
                    self._log(f'CTP528 boundary type: {type(out_CTP528)}')
        except Exception:
            pass

        nMTF80 = mtf_points.get('MTF80', float('nan'))
        nMTF50 = mtf_points.get('MTF50', float('nan'))
        nMTF30 = mtf_points.get('MTF30', float('nan'))
        nMTF10 = mtf_points.get('MTF10', float('nan'))

        # Gather CTP404 plot data
        ctp404 = self.ctp404
        im_CTP404 = getattr(ctp404, 'image', None)
        # roi_coordinates is list of (x_circle, y_circle)
        roi_coords = getattr(ctp404, 'roi_coordinates', [])
        if roi_coords:
            n_rois = len(roi_coords)
            n_pts = len(roi_coords[0][0])
            ROI_CTP404 = np.zeros((2, n_pts, n_rois))
            for i, (x_circ, y_circ) in enumerate(roi_coords):
                ROI_CTP404[0, :, i] = x_circ
                ROI_CTP404[1, :, i] = y_circ
        else:
            ROI_CTP404 = np.zeros((2, 0, 0))
        # Attempt to get an outer boundary for CTP404 if provided by the analyzer
        if hasattr(ctp404, 'get_plot_data'):
            try:
                p404 = ctp404.get_plot_data()
                out_CTP404 = p404.get('outer_boundary', getattr(ctp404, 'boundary', ([], [])))
            except Exception:
                out_CTP404 = getattr(ctp404, 'boundary', ([], []))
        else:
            out_CTP404 = getattr(ctp404, 'boundary', ([], []))

        # If the analyzer didn't provide a usable outer boundary, try to
        # compute one from the image and center using the shared utility.
        try:
            from alexandria.utils import compute_phantom_boundary
            # normalize out_CTP404 into arrays if present
            try:
                arr = np.array(out_CTP404)
                empty404 = arr.size == 0 or (arr.ndim == 2 and arr.shape[1] == 0)
            except Exception:
                empty404 = True

            if empty404:
                if getattr(ctp404, 'image', None) is not None and getattr(ctp404, 'center', None) is not None:
                    _, (bx, by) = compute_phantom_boundary(ctp404.image, ctp404.center, getattr(ctp404, 'pixel_spacing', None), threshold=400, fallback_threshold=300)
                    out_CTP404 = (np.array(bx), np.array(by))
        except Exception:
            pass

        # scaling pts from earlier spatial-scaling
        pts = getattr(self, 'scaling_pts', None)

        # Gather CTP486 plot data
        ctp486 = self.ctp486
        im_CTP486 = getattr(ctp486, 'image', None)
        roi_boxes = ctp486.get_plot_data().get('roi_boxes', []) if hasattr(ctp486, 'get_plot_data') else getattr(ctp486, 'roi_coordinates', [])
        ROI_CTP486 = np.array(roi_boxes)
        out_CTP486 = getattr(ctp486, 'boundary', ([], []))

        # If the uniformity analyzer did not compute a boundary, attempt to
        # compute one using the same utility.
        try:
            from alexandria.utils import compute_phantom_boundary
            try:
                arr6 = np.array(out_CTP486)
                empty486 = arr6.size == 0 or (arr6.ndim == 2 and arr6.shape[1] == 0)
            except Exception:
                empty486 = True

            if empty486:
                if getattr(ctp486, 'image', None) is not None and getattr(ctp486, 'center', None) is not None:
                    _, (bx6, by6) = compute_phantom_boundary(ctp486.image, ctp486.center, getattr(ctp486, 'pixel_spacing', None), threshold=400, fallback_threshold=300)
                    out_CTP486 = (np.array(bx6), np.array(by6))
        except Exception:
            pass

        # Helper to robustly plot boundaries from multiple possible formats
        def _plot_boundary(ax, b, linewidth=2, **kwargs):
            if b is None:
                return
            try:
                # dict-like with keys 0/1 or 'x'/'y'
                if isinstance(b, dict):
                    xs = None
                    ys = None
                    if 0 in b and 1 in b:
                        xs = np.array(b[0])
                        ys = np.array(b[1])
                    else:
                        xs = np.array(b.get('x', []))
                        ys = np.array(b.get('y', []))
                    if xs.size and ys.size:
                        ax.plot(xs, ys, color='r', linewidth=linewidth, zorder=5, **kwargs)
                        return

                arr = np.array(b)
                # Nx2 array of (x,y) pairs
                if arr.ndim == 2 and arr.shape[1] == 2:
                    xs = arr[:, 0]
                    ys = arr[:, 1]
                    ax.plot(xs, ys, color='r', linewidth=linewidth, zorder=5, **kwargs)
                    return
                # 2xN array like [x_array, y_array]
                if arr.ndim == 2 and arr.shape[0] == 2:
                    xs = arr[0]
                    ys = arr[1]
                    ax.plot(xs, ys, color='r', linewidth=linewidth, zorder=5, **kwargs)
                    return
                # tuple/list of two iterables
                if isinstance(b, (list, tuple)) and len(b) >= 2:
                    xs = np.array(b[0])
                    ys = np.array(b[1])
                    if xs.size and ys.size:
                        ax.plot(xs, ys, color='r', linewidth=linewidth, zorder=5, **kwargs)
                        return
            except Exception:
                pass

        # Create a GridSpec layout: left area is a 2x2 legacy panel (like the
        # original 2x2 layout). The right column contains vertically stacked
        # CTP528 profiles. If there are more profiles than two rows, the
        # profile column will extend downward while the 2x2 legacy panel
        # remains in the top-left portion.
        from matplotlib.gridspec import GridSpec

        profiles = getattr(ctp528, 'profiles', []) or []
        n_profiles = len(profiles)
        # Fix the left area to a 2x2 layout. Profiles on the right will be
        # created using a subgridspec so they evenly share the same vertical
        # span as the 2x2 block instead of growing the overall figure.
        n_rows = 2
        # Reduce overall width and increase vertical height per request
        fig_width = fsize * 0.9
        fig_height = 10
        fig = plt.figure(figsize=(fig_width, fig_height))
        # Use three columns: two for the 2x2 legacy block, one narrow for profiles
        # Narrow the profile column (less horizontal space) and allow more
        # vertical room by increasing figure height.
        # Increase the profile column width by 1.2x (previously 1.2 -> now 1.44)
        gs = GridSpec(n_rows, 3, figure=fig, width_ratios=[3, 3, 1.44], hspace=0.18)

        # Left 2x2 legacy panels (occupy rows 0..1 and cols 0..1)
        ax0 = fig.add_subplot(gs[0, 0])
        if im_CTP528 is not None:
            ax0.imshow(im_CTP528, cmap='gray', vmin=Vmin, vmax=Vmax)
        if lpx is not None and lpy is not None:
            ax0.plot(lpx, lpy, '-r')
        if out_CTP528 and len(out_CTP528) == 2:
            try:
                _plot_boundary(ax0, out_CTP528, linewidth=2)
            except Exception:
                pass
        ax0.set_title('CTP528')
        ax0.axis('off')

        # CTP528 MTF (top-right of the 2x2 left block)
        ax1 = fig.add_subplot(gs[0, 1])
        if lp is not None and nMTF is not None:
            ax1.plot(lp, nMTF)
        ax1.plot([nMTF50, nMTF10], [0.5, 0.1], 'or', mfc='none')
        ax1.set_title('Aggregated Normalized MTF')
        ax1.set_ylabel('Normalized MTF')
        ax1.set_xlabel('lp/mm')
        ax1.grid()
        # Ensure the MTF plot is visually square. Prefer set_box_aspect
        # (available in newer matplotlib) and fall back to set_aspect.
        try:
            ax1.set_box_aspect(1)
        except Exception:
            try:
                ax1.set_aspect('equal', adjustable='box')
            except Exception:
                pass

        # CTP404 image (bottom-left of the 2x2 left block)
        ax2 = fig.add_subplot(gs[1, 0])
        if im_CTP404 is not None:
            ax2.imshow(im_CTP404, cmap='gray', vmin=Vmin, vmax=Vmax)
        try:
            for i in range(ROI_CTP404.shape[2]):
                ax2.plot(ROI_CTP404[0, :, i], ROI_CTP404[1, :, i], 'r')
        except Exception:
            pass
        # Log and plot computed outer boundary if available (robust to formats)
        try:
            if out_CTP404 is None:
                self._log('CTP404: no outer boundary found')
            else:
                # Log a concise description
                try:
                    b_arr = np.array(out_CTP404)
                    self._log(f'CTP404 boundary shape: {b_arr.shape}')
                except Exception:
                    self._log(f'CTP404 boundary type: {type(out_CTP404)}')
        except Exception:
            pass
        _plot_boundary(ax2, out_CTP404, linewidth=2)
        ax2.set_title('CTP404')
        ax2.axis('off')
        if pts is not None and len(pts) >= 4:
            try:
                ax2.plot(pts[0], pts[1], 'g')
                ax2.plot(pts[2], pts[3], 'g')
            except Exception:
                pass

        # CTP486 image (bottom-right of the 2x2 left block)
        ax3 = fig.add_subplot(gs[1, 1])
        if im_CTP486 is not None:
            ax3.imshow(im_CTP486, cmap='gray', vmin=Vmin, vmax=Vmax)
        # Log and plot computed outer boundary for CTP486 as well
        try:
            if out_CTP486 is None:
                self._log('CTP486: no outer boundary found')
            else:
                try:
                    b_arr = np.array(out_CTP486)
                    self._log(f'CTP486 boundary shape: {b_arr.shape}')
                except Exception:
                    self._log(f'CTP486 boundary type: {type(out_CTP486)}')
        except Exception:
            pass
        _plot_boundary(ax3, out_CTP486, linewidth=2)
        try:
            b = ROI_CTP486
            for r in range(b.shape[0]):
                ax3.plot([b[r, 0], b[r, 0]], [b[r, 2], b[r, 3]], 'r')
                ax3.plot([b[r, 1], b[r, 1]], [b[r, 2], b[r, 3]], 'r')
                ax3.plot([b[r, 0], b[r, 1]], [b[r, 2], b[r, 2]], 'r')
                ax3.plot([b[r, 0], b[r, 1]], [b[r, 3], b[r, 3]], 'r')
        except Exception:
            pass
        ax3.set_title('CTP486')
        ax3.axis('off')

        # Right column: vertically stacked profiles for CTP528. Use a
        # subgridspec inside the third column so the profiles share the same
        # vertical span as the 2x2 left block.
        n_to_show = n_profiles
        profile_axes = []
        if n_to_show > 0:
            subgs = gs[:, 2].subgridspec(n_to_show, 1, hspace=0.08)
            for i in range(n_to_show):
                sharex = profile_axes[0] if profile_axes else None
                axp = fig.add_subplot(subgs[i, 0], sharex=sharex)
                prof = profiles[i]
                axp.plot(range(len(prof)), prof, linewidth=1.2)
                axp.grid(True, alpha=0.3)
                axp.text(0.02, 0.95, f'LP{i+1}', transform=axp.transAxes, fontsize=8, va='top')
                if i != n_to_show - 1:
                    axp.tick_params(labelbottom=False)
                else:
                    axp.set_xlabel('Sample Index')
                profile_axes.append(axp)

        # Tight layout and save — handle tight_layout incompatibility warnings
        ds0 = self.dicom_set[0] if self.dicom_set else None
        date_str = f"{ds0.StudyDate[0:4]}-{ds0.StudyDate[4:6]}-{ds0.StudyDate[6:8]}" if ds0 is not None else 'unknown'
        unit_name = ds0.StationName if ds0 is not None else 'unit'
        base_name = f"CatPhan_{unit_name}_{date_str}"
        save_path = self.output_path / f"{base_name}_Legacy.png"

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            try:
                fig.tight_layout()
            except Exception:
                # tight_layout can raise for some Axes types; ignore and try fallback
                pass

            # Detect the specific tight_layout warning message
            incompatible = any(
                ("not compatible with tight_layout" in str(x.message)) or
                ("includes Axes that are not compatible with tight_layout" in str(x.message))
                for x in w
            )

            try:
                if incompatible:
                    fig.set_constrained_layout(False)
                    # attempt a reasonable manual adjustment
                    fig.subplots_adjust(hspace=0.12, wspace=0.08)
                    fig.savefig(save_path)
                else:
                    fig.savefig(save_path)
            except Exception:
                # As a last resort, disable constrained layout and save
                try:
                    fig.set_constrained_layout(False)
                    fig.subplots_adjust(hspace=0.12, wspace=0.08)
                    fig.savefig(save_path)
                except Exception:
                    # If saving still fails, propagate the error
                    plt.close(fig)
                    raise

        plt.close(fig)
        self._log(f"Legacy plot saved: {save_path}")
        return save_path

    def _build_ctp404_results(self, raw_results: Dict) -> Dict:
        """
        Normalize CTP404 results to the legacy report schema.
        """
        contrast_rois = []
        for roi in raw_results.get('contrast', []):
            contrast_rois.append([
                roi['roi_number'],
                roi['material'],
                roi['mean_hu'],
                roi['std_hu']
            ])

        idx = self.slice_indices['ctp404']
        image = self.dicom_set[idx].pixel_array
        pixel_spacing = self.dicom_set[idx].PixelSpacing
        slice_thickness = CatPhanGeometry.calculate_slice_thickness(
            image,
            pixel_spacing,
            self.module_centers['ctp404']
        )

        return {
            'contrast_rois': contrast_rois,
            'low_contrast_visibility': raw_results.get('LCV_percent'),
            'slice_thickness_mm': slice_thickness
        }

    def _build_ctp486_results(self, raw_results: Dict) -> Dict:
        """
        Normalize uniformity results to the legacy report schema.
        """
        regions = []
        for name in ['centre', 'north', 'south', 'east', 'west']:
            stats = raw_results.get(name)
            if stats is None:
                continue
            regions.append([name.title(), stats.get('mean'), stats.get('std')])

        uniformity = raw_results.get('uniformity')

        return {
            'regions': regions,
            'uniformity_percent': uniformity
        }

    def _calculate_spatial_scaling(self, ct_point, cb_point):
        """
        Calculate X and Y scaling using geometric features.
        """
        from scipy.interpolate import interpn
        from scipy.signal import find_peaks

        idx = self.slice_indices['ctp404']
        
        # 3 slice averaging
        if idx <= 0:
            im1 = self.dicom_set[idx].pixel_array
            im2 = self.dicom_set[idx + 1].pixel_array
            im3 = self.dicom_set[idx + 1].pixel_array
        elif idx >= len(self.dicom_set) - 1:
            im1 = self.dicom_set[idx].pixel_array
            im2 = self.dicom_set[idx - 1].pixel_array
            im3 = self.dicom_set[idx - 1].pixel_array
        else:
            im1 = self.dicom_set[idx].pixel_array
            im2 = self.dicom_set[idx + 1].pixel_array
            im3 = self.dicom_set[idx - 1].pixel_array
        im = (im1 + im2 + im3) / 3
        
        # Get image size and pixel spacing
        sz = (self.dicom_set[idx].Rows, self.dicom_set[idx].Columns)
        space = self.dicom_set[idx].PixelSpacing
        
        # Index for x and y pixel positions
        x = np.linspace(0, (sz[0] - 1), sz[0])
        y = np.linspace(0, (sz[1] - 1), sz[1])
        
        # Get center from averaging top and bottom air ROI centers
        cmid = [(ct_point[0] + cb_point[0]) / 2, (ct_point[1] + cb_point[1]) / 2]
        
        # Get coordinates through center of top and bottom ROIs
        r = 70
        t_offset = self.rotation_offset
        
        xscale_xcoord = [
            cmid[0] - r / space[0] * np.cos(t_offset * 2 * np.pi / 360),
            cmid[0] + r / space[0] * np.cos(t_offset * 2 * np.pi / 360)
        ]
        xscale_ycoord = [
            cmid[1] - r / space[0] * np.sin(t_offset * 2 * np.pi / 360),
            cmid[1] + r / space[0] * np.sin(t_offset * 2 * np.pi / 360)
        ]
        l = np.sqrt((xscale_xcoord[1] - xscale_xcoord[0]) ** 2 +
                    (xscale_ycoord[1] - xscale_ycoord[0]) ** 2)
        
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
        xscale_xcoord = [
            cmid[0] - r / space[0] * np.cos(t_offset * 2 * np.pi / 360),
            cmid[0] + r / space[0] * np.cos(t_offset * 2 * np.pi / 360)
        ]
        xscale_ycoord = [
            cmid[1] - r / space[0] * np.sin(t_offset * 2 * np.pi / 360),
            cmid[1] + r / space[0] * np.sin(t_offset * 2 * np.pi / 360)
        ]
        
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
            except Exception:
                continue
        
        # If we still don't have enough peaks, raise an error with diagnostic info
        if peaks1 is None or len(peaks1) < 2 or peaks2 is None or len(peaks2) < 2:
            raise ValueError(
                "Could not find enough peaks for spatial scaling calculation. "
                f"Found {len(peaks1) if peaks1 is not None else 0} peaks in direction 1, "
                f"{len(peaks2) if peaks2 is not None else 0} peaks in direction 2. "
                f"Derivative ranges: df1=[{df1.min():.1f}, {df1.max():.1f}], "
                f"df2=[{df2.min():.1f}, {df2.max():.1f}]"
            )
        
        # Calculate scaling from edge-to-edge distances
        xscale1 = np.abs((ltmp[peaks1[0]] - ltmp[peaks1[len(peaks1) - 2]])) * space[0]
        xscale2 = np.abs((ltmp[peaks1[1]] - ltmp[peaks1[len(peaks1) - 1]])) * space[0]
        yscale1 = np.abs((ltmp[peaks2[0]] - ltmp[peaks2[len(peaks2) - 2]])) * space[0]
        yscale2 = np.abs((ltmp[peaks2[1]] - ltmp[peaks2[len(peaks2) - 1]])) * space[0]
        
        # Average and convert to cm
        x_scale = ((xscale1 + xscale2) / 2) / 10
        y_scale = ((yscale1 + yscale2) / 2) / 10
        
        return x_scale, y_scale, pts
    
    def _log(self, message):
        """
        Write a message to the log file and print to console.
        
        Args:
            message: Message to log
        """
        print(message)
        
        if self.log_file:
            with open(self.log_file, 'a') as f:
                f.write(message + '\n')
    
    def open_log(self, log_filename='ScriptLog.txt'):
        """
        Open a log file for writing.
        
        Args:
            log_filename: Name of the log file
        """
        self.log_file = self.output_path / log_filename
        
        with open(self.log_file, 'w') as f:
            f.write('CatPhan Analysis Script Log\n')
            f.write(f'Date/Time: {datetime.datetime.now()}\n')
            f.write(f'Path: {self.dicom_path}\n')
            f.write('=' * 60 + '\n\n')
    
    def close_log(self):
        """Close the log file."""
        if self.log_file:
            self._log("\n\nAnalysis complete.")
            self.log_file = None
