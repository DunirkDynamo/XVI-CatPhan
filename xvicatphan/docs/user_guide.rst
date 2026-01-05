User Guide
==========

This guide provides detailed information about using the CatPhan Analysis package.

Architecture Overview
---------------------

The package is organized around a modular, object-oriented architecture:

* **Executive Class**: :class:`~catphan_analysis.analyzer.CatPhanAnalyzer` coordinates the workflow
* **Analysis Modules**: :class:`~catphan_analysis.modules.CTP404Module`, :class:`~catphan_analysis.modules.CTP486Module`, :class:`~catphan_analysis.modules.CTP528Module`
* **Utilities**: Geometric calculations and image processing helpers
* **DICOM Listener**: Automated file monitoring and processing

Working with CatPhanAnalyzer
-----------------------------

The :class:`~catphan_analysis.analyzer.CatPhanAnalyzer` class is the main entry point for analysis.

Initialization
~~~~~~~~~~~~~~

.. code-block:: python

   from catphan_analysis import CatPhanAnalyzer

   analyzer = CatPhanAnalyzer(
       dicom_path='/path/to/dicom',
       output_path='/path/to/output',  # optional
       catphan_model='500'              # or '504'
   )

Step-by-Step Analysis
~~~~~~~~~~~~~~~~~~~~~

For more control, you can run each step individually:

.. code-block:: python

   # Load DICOM files
   num_files = analyzer.load_dicom_files()
   print(f"Loaded {num_files} files")

   # Locate modules
   indices = analyzer.locate_modules()
   print(f"CTP528 at slice {indices['ctp528']}")

   # Find centers and rotation
   analyzer.find_module_centers()
   analyzer.find_rotation()

   # Initialize module instances
   analyzer.initialize_modules()

   # Access individual modules
   ctp404_results = analyzer.ctp404.analyze()
   ctp486_results = analyzer.ctp486.analyze()
   ctp528_results = analyzer.ctp528.analyze()

Using Individual Modules
-------------------------

Each analysis module can be used independently.

CTP404 Module (Contrast)
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from catphan_analysis.modules import CTP404Module

   ctp404 = CTP404Module(
       dicom_set=dicom_datasets,
       slice_index=50,
       center=(256, 256),
       rotation_offset=0.0
   )

   # Prepare image
   ctp404.prepare_image()

   # Run specific analyses
   contrast_results = ctp404.analyze_contrast()
   lcv = ctp404.calculate_low_contrast_visibility()
   x_scale, y_scale, _ = ctp404.calculate_spatial_scaling()
   thickness = ctp404.measure_slice_thickness()

   # Or run complete analysis
   all_results = ctp404.analyze()

CTP486 Module (Uniformity)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from catphan_analysis.modules import CTP486Module

   ctp486 = CTP486Module(
       dicom_set=dicom_datasets,
       slice_index=30,
       center=(256, 256),
       roi_box_size=15,  # mm
       roi_offset=50     # mm
   )

   results = ctp486.analyze()
   uniformity = results['uniformity_percent']

CTP528 Module (Resolution)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from catphan_analysis.modules import CTP528Module

   ctp528 = CTP528Module(
       dicom_set=dicom_datasets,
       slice_index=86,
       center=(256, 256),
       rotation_offset=0.0
   )

   results = ctp528.analyze()
   mtf_10 = results['mtf_10']  # 10% MTF in lp/mm

Automated Processing
--------------------

DICOM Listener
~~~~~~~~~~~~~~

The :class:`~catphan_analysis.dicom_listener.DICOMListener` monitors a directory for incoming files:

.. code-block:: python

   from catphan_analysis import DICOMListener

   listener = DICOMListener(
       base_path='/path/to/receiver',
       sleep_interval=5,
       wait_cycles=8
   )

   # Set callback for when files are ready
   def process_callback(data_path):
       analyzer = CatPhanAnalyzer(data_path)
       analyzer.analyze()
       analyzer.generate_report()

   listener.set_analysis_callback(process_callback)
   listener.start()  # Blocks until Ctrl+C

Batch Processing
----------------

Process multiple datasets:

.. code-block:: python

   datasets = [
       '/path/to/dataset1',
       '/path/to/dataset2',
       '/path/to/dataset3'
   ]

   for dataset_path in datasets:
       try:
           analyzer = CatPhanAnalyzer(dataset_path)
           analyzer.open_log()
           results = analyzer.analyze()
           analyzer.generate_report()
           analyzer.close_log()
       except Exception as e:
           print(f"Error with {dataset_path}: {e}")

Custom Workflows
----------------

You can create custom analysis workflows by combining components:

.. code-block:: python

   from catphan_analysis import CatPhanAnalyzer
   from catphan_analysis.utils.geometry import CatPhanGeometry

   # Load data
   analyzer = CatPhanAnalyzer('/path/to/dicom')
   analyzer.load_dicom_files()

   # Custom preprocessing
   # ... your code here ...

   # Continue with standard analysis
   analyzer.locate_modules()
   analyzer.find_module_centers()
   
   # Custom analysis on specific module
   analyzer.initialize_modules()
   contrast_results = analyzer.ctp404.analyze_contrast()
   
   # Custom filtering or post-processing
   for roi_data in contrast_results:
       # ... your custom logic ...
       pass

Error Handling
--------------

Always wrap analysis in try-except blocks:

.. code-block:: python

   try:
       analyzer = CatPhanAnalyzer('/path/to/dicom')
       analyzer.open_log()
       results = analyzer.analyze()
       analyzer.generate_report()
   except FileNotFoundError:
       print("DICOM files not found")
   except ValueError as e:
       print(f"Invalid data: {e}")
   except Exception as e:
       print(f"Analysis failed: {e}")
   finally:
       if analyzer.log_file:
           analyzer.close_log()

Best Practices
--------------

1. **Always open/close logs** when using CatPhanAnalyzer
2. **Check file count** after loading to ensure data is present
3. **Use try-except** for robust error handling
4. **Validate results** before using them
5. **Keep original files** - analysis creates copies for output
