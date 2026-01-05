CatPhan Analysis Documentation
================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   installation
   quickstart
   user_guide
   api_reference
   examples

Overview
--------

A professional, object-oriented software package for analyzing CatPhan phantom DICOM images. 
This package provides modular, class-based analysis of CTP404, CTP486, and CTP528 modules.

Features
--------

* **Modular Architecture**: Each analysis module (CTP404, CTP486, CTP528) is implemented as a separate class
* **Executive Class**: ``CatPhanAnalyzer`` coordinates all analysis modules
* **Automated Processing**: DICOM listener for automated file reception and analysis
* **Comprehensive Analysis**:

  * CTP404: Contrast, HU accuracy, spatial scaling, slice thickness
  * CTP486: Image uniformity
  * CTP528: Spatial resolution (MTF)

Quick Start
-----------

.. code-block:: python

   from catphan_analysis import CatPhanAnalyzer

   # Create analyzer
   analyzer = CatPhanAnalyzer('/path/to/dicom/files')
   
   # Run analysis
   analyzer.open_log()
   results = analyzer.analyze()
   analyzer.generate_report()
   analyzer.close_log()

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
