Examples
========

This page provides comprehensive examples of using the CatPhan Analysis package.

Example 1: Basic Complete Analysis
-----------------------------------

The simplest usage pattern:

.. code-block:: python

   from catphan_analysis import CatPhanAnalyzer

   # Create analyzer
   analyzer = CatPhanAnalyzer(
       dicom_path='C:/Data/CatPhan',
       output_path='C:/Data/CatPhan/results'
   )
   
   # Run complete analysis
   analyzer.open_log()
   results = analyzer.analyze()
   report_path = analyzer.generate_report()
   analyzer.close_log()
   
   print(f"Analysis complete! Report: {report_path}")

Example 2: Step-by-Step Analysis
---------------------------------

For more control over the process:

.. code-block:: python

   from catphan_analysis import CatPhanAnalyzer

   # Create analyzer
   analyzer = CatPhanAnalyzer(dicom_path='C:/Data/CatPhan')
   
   # Load DICOM files
   num_files = analyzer.load_dicom_files()
   print(f"Loaded {num_files} DICOM files")
   
   # Locate modules
   indices = analyzer.locate_modules()
   print(f"Module locations:")
   for module, idx in indices.items():
       print(f"  {module}: slice {idx}")
   
   # Find centers
   centers = analyzer.find_module_centers()
   print(f"Module centers:")
   for module, center in centers.items():
       print(f"  {module}: ({center[0]:.1f}, {center[1]:.1f})")
   
   # Find rotation
   rotation = analyzer.find_rotation()
   print(f"Rotation: {rotation:.2f} degrees")
   
   # Initialize and analyze modules
   analyzer.initialize_modules()
   
   # Analyze each module separately
   print("--- CTP404 Analysis ---")
   results_404 = analyzer.ctp404.analyze()
   print(f"Low Contrast Visibility: {results_404['low_contrast_visibility']:.3f}%")
   
   print("--- CTP486 Analysis ---")
   results_486 = analyzer.ctp486.analyze()
   print(f"Uniformity: {results_486['uniformity_percent']:.2f}%")
   
   print("--- CTP528 Analysis ---")
   results_528 = analyzer.ctp528.analyze()
   print(f"10% MTF: {results_528['mtf_10']:.3f} lp/mm")
   
   # Generate report
   analyzer.generate_report()

Example 3: Using Individual Modules
------------------------------------

Work with specific analysis modules:

.. code-block:: python

   from catphan_analysis import CatPhanAnalyzer
   from catphan_analysis.modules import CTP404Module

   # First, load DICOM data
   analyzer = CatPhanAnalyzer(dicom_path='C:/Data/CatPhan')
   analyzer.load_dicom_files()
   analyzer.locate_modules()
   analyzer.find_module_centers()
   analyzer.find_rotation()
   
   # Create individual module
   ctp404 = CTP404Module(
       dicom_set=analyzer.dicom_set,
       slice_index=analyzer.slice_indices['ctp404'],
       center=analyzer.module_centers['ctp404'],
       rotation_offset=analyzer.rotation_offset
   )
   
   # Prepare image
   ctp404.prepare_image()
   
   # Run specific analyses
   contrast_results = ctp404.analyze_contrast()
   
   print("Contrast ROI Results:")
   for roi_data in contrast_results:
       roi_num, material, mean, std = roi_data
       print(f"  ROI {roi_num} ({material}): {mean:.1f} ± {std:.1f} HU")
   
   # Calculate specific metrics
   lcv = ctp404.calculate_low_contrast_visibility()
   print(f"Low Contrast Visibility: {lcv:.3f}%")
   
   # Get summary
   summary = ctp404.get_results_summary()
   print("Summary:")
   for key, value in summary.items():
       print(f"  {key}: {value}")

Example 4: Custom Analysis Workflow
------------------------------------

Create a custom workflow with preprocessing:

.. code-block:: python

   from catphan_analysis import CatPhanAnalyzer
   import numpy as np

   # Create analyzer
   analyzer = CatPhanAnalyzer(
       dicom_path='C:/Data/CatPhan',
       catphan_model='500'
   )
   
   # Load data
   analyzer.load_dicom_files()
   
   # Custom filtering or preprocessing
   print(f"Total slices: {len(analyzer.dicom_set)}")
   
   # Check image quality
   first_image = analyzer.dicom_set[0].pixel_array
   mean_hu = np.mean(first_image)
   print(f"Mean HU of first slice: {mean_hu:.1f}")
   
   # Continue with analysis
   analyzer.locate_modules()
   analyzer.find_module_centers()
   analyzer.find_rotation()
   analyzer.initialize_modules()
   
   # Run analysis on specific modules
   results_404 = analyzer.ctp404.analyze()
   
   # Custom post-processing
   for roi_data in results_404['contrast_rois']:
       roi_num, material, mean, std = roi_data
       
       # Check specific materials
       if material == 'Air':
           deviation = abs(mean - (-1000))
           print(f"Air ROI deviation from -1000 HU: {deviation:.1f}")
       elif material == 'none':  # Water
           deviation = abs(mean - 0)
           print(f"Water ROI deviation from 0 HU: {deviation:.1f}")
   
   # Generate report
   analyzer.generate_report()

Example 5: Batch Processing
----------------------------

Process multiple datasets:

.. code-block:: python

   from pathlib import Path
   from catphan_analysis import CatPhanAnalyzer

   # List of directories to process
   base_dir = Path('C:/Data/CatPhan')
   datasets = list(base_dir.glob('Dataset_*'))
   
   results_summary = []
   
   for dataset_path in datasets:
       print(f"Processing: {dataset_path.name}")
       
       try:
           analyzer = CatPhanAnalyzer(dicom_path=dataset_path)
           analyzer.open_log()
           results = analyzer.analyze()
           analyzer.generate_report()
           analyzer.close_log()
           
           # Collect key metrics
           results_summary.append({
               'dataset': dataset_path.name,
               'uniformity': results['ctp486']['uniformity_percent'],
               'mtf_10': results['ctp528']['mtf_10'],
               'lcv': results['ctp404']['low_contrast_visibility']
           })
           
           print(f"  ✓ Complete")
           
       except Exception as e:
           print(f"  ✗ Error: {e}")
   
   # Print summary
   print("\n" + "="*60)
   print("Batch Processing Summary")
   print("="*60)
   for result in results_summary:
       print(f"\n{result['dataset']}:")
       print(f"  Uniformity: {result['uniformity']:.2f}%")
       print(f"  10% MTF: {result['mtf_10']:.3f} lp/mm")
       print(f"  LCV: {result['lcv']:.3f}%")

Example 6: DICOM Listener with Custom Callback
-----------------------------------------------

Set up automated processing:

.. code-block:: python

   from catphan_analysis import CatPhanAnalyzer, DICOMListener
   from pathlib import Path
   import datetime

   def custom_analysis_callback(data_path):
       """Custom callback for when files are ready."""
       print(f"\n{'='*60}")
       print(f"New dataset received: {data_path}")
       print(f"Time: {datetime.datetime.now()}")
       print(f"{'='*60}\n")
       
       try:
           # Run analysis
           analyzer = CatPhanAnalyzer(data_path)
           analyzer.open_log()
           results = analyzer.analyze()
           analyzer.generate_report()
           analyzer.close_log()
           
           # Send notification (example)
           uniformity = results['ctp486']['uniformity_percent']
           if uniformity > 5.0:
               print(f"WARNING: High uniformity: {uniformity:.2f}%")
           
           print("Analysis complete!")
           
       except Exception as e:
           print(f"Error during analysis: {e}")
           # Could send error notification here
   
   # Create listener
   listener = DICOMListener(
       base_path='C:/DICOM_Receiver',
       sleep_interval=5,
       wait_cycles=8
   )
   
   # Set callback
   listener.set_analysis_callback(custom_analysis_callback)
   
   # Start listening
   print("Starting DICOM listener...")
   print("Press Ctrl+C to stop")
   
   try:
       listener.start()
   except KeyboardInterrupt:
       print("\nStopping listener...")
       listener.stop()

Example 7: Quality Assurance Checks
------------------------------------

Perform QA checks on results:

.. code-block:: python

   from catphan_analysis import CatPhanAnalyzer

   def check_qa_results(results):
       """Perform QA checks on analysis results."""
       
       issues = []
       
       # Check uniformity
       uniformity = results['ctp486']['uniformity_percent']
       if uniformity > 5.0:
           issues.append(f"High uniformity: {uniformity:.2f}% (limit: 5.0%)")
       
       # Check MTF
       mtf_10 = results['ctp528']['mtf_10']
       if mtf_10 < 0.5:
           issues.append(f"Low 10% MTF: {mtf_10:.3f} lp/mm (min: 0.5)")
       
       # Check HU accuracy
       for roi_data in results['ctp404']['contrast_rois']:
           roi_num, material, mean, std = roi_data
           
           if material == 'Air':
               if abs(mean - (-1000)) > 50:
                   issues.append(f"Air HU deviation: {mean:.1f} HU")
           elif material == 'none':  # Water
               if abs(mean) > 10:
                   issues.append(f"Water HU deviation: {mean:.1f} HU")
       
       return issues

   # Run analysis
   analyzer = CatPhanAnalyzer('C:/Data/CatPhan')
   analyzer.open_log()
   results = analyzer.analyze()
   analyzer.generate_report()
   analyzer.close_log()

   # Check results
   issues = check_qa_results(results)

   if issues:
       print("QA ISSUES FOUND:")
       for issue in issues:
           print(f"  ⚠ {issue}")
   else:
       print("✓ All QA checks passed!")

Example 8: Accessing Raw Data
------------------------------

Access raw analysis data for custom processing:

.. code-block:: python

   from catphan_analysis import CatPhanAnalyzer
   import matplotlib.pyplot as plt
   import numpy as np

   # Run analysis
   analyzer = CatPhanAnalyzer('C:/Data/CatPhan')
   analyzer.load_dicom_files()
   analyzer.locate_modules()
   analyzer.find_module_centers()
   analyzer.find_rotation()
   analyzer.initialize_modules()

   # Access CTP528 module
   ctp528 = analyzer.ctp528
   results = ctp528.analyze()

   # Get raw MTF data
   mtf_array = results['mtf_array']
   lp_frequencies = results['lp_frequencies']

   # Create custom plot
   plt.figure(figsize=(10, 6))
   plt.plot(lp_frequencies, mtf_array, 'b-', linewidth=2)
   plt.axhline(y=0.5, color='r', linestyle='--', label='50% MTF')
   plt.axhline(y=0.1, color='g', linestyle='--', label='10% MTF')
   plt.xlabel('Spatial Frequency (lp/mm)')
   plt.ylabel('Normalized MTF')
   plt.title('Custom MTF Plot')
   plt.grid(True)
   plt.legend()
   plt.savefig('custom_mtf_plot.png', dpi=300)
   plt.close()

   print("Custom plot saved!")
