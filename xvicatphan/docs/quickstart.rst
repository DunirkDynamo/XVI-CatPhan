Quick Start Guide
=================

This guide will help you get started with CatPhan Analysis in just a few minutes.

Basic Analysis
--------------

The simplest way to analyze CatPhan images:

.. code-block:: python

   from catphan_analysis import CatPhanAnalyzer

   # Create analyzer
   analyzer = CatPhanAnalyzer('/path/to/dicom/files')
   
   # Run complete analysis
   analyzer.open_log()
   results = analyzer.analyze()
   analyzer.generate_report()
   analyzer.close_log()

This will:

1. Load DICOM files from the specified directory
2. Locate all three CatPhan modules (CTP404, CTP486, CTP528)
3. Analyze each module
4. Generate a report with results and plots

Command-Line Usage
------------------

You can also use the command-line interface:

.. code-block:: bash

   # Basic analysis
   python main.py /path/to/dicom/files

   # With output directory
   python main.py /path/to/dicom/files --output /path/to/output

   # Specify CatPhan model
   python main.py /path/to/dicom/files --model 504

Automated DICOM Listening
--------------------------

For automated processing of incoming DICOM files:

.. code-block:: bash

   python listen_and_analyze.py /path/to/dicom/receiver

This will monitor the directory for new DICOM files and automatically trigger analysis when files are received.

Understanding Results
---------------------

The analysis produces:

* **Text Report**: CSV-formatted results file with all measurements
* **Plots**: Visual representation of the modules and ROIs
* **Log File**: Detailed log of the analysis process

Key Measurements
~~~~~~~~~~~~~~~~

**CTP404 (Contrast)**:

* HU values for 9 materials
* Low contrast visibility
* Spatial scaling (X/Y)
* Slice thickness

**CTP486 (Uniformity)**:

* Mean HU in 5 regions
* Uniformity percentage

**CTP528 (Resolution)**:

* MTF at 10%, 30%, 50%, 80%

Next Steps
----------

* Read the :doc:`user_guide` for detailed information
* See :doc:`examples` for more usage patterns
* Check the :doc:`api_reference` for complete API documentation
