Installation
============

Requirements
------------

* Python 3.7 or higher
* numpy >= 1.19.0
* scipy >= 1.5.0
* matplotlib >= 3.3.0
* pydicom >= 2.0.0

Installation Steps
------------------

Using pip
~~~~~~~~~

.. code-block:: bash

   pip install -r requirements.txt

For development installation:

.. code-block:: bash

   pip install -e .

From Source
~~~~~~~~~~~

1. Clone the repository:

   .. code-block:: bash

      git clone https://github.com/yourusername/catphan-analysis.git
      cd catphan-analysis

2. Install dependencies:

   .. code-block:: bash

      pip install -r requirements.txt

3. (Optional) Install the package:

   .. code-block:: bash

      pip install -e .

Verifying Installation
----------------------

Test the installation by importing the package:

.. code-block:: python

   from catphan_analysis import CatPhanAnalyzer
   print("Installation successful!")

Optional Dependencies
---------------------

For documentation building:

.. code-block:: bash

   pip install sphinx sphinx-rtd-theme
