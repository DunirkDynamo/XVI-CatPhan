"""
CatPhan Analysis Package

A professional software package for analyzing CatPhan phantom DICOM images.
Provides modular, class-based analysis of CTP404, CTP486, and CTP528 modules.
"""

from .analyzer import CatPhanAnalyzer
from .dicom_listener import DICOMListener
from alexandria import CTP404Analyzer, UniformityAnalyzer, HighContrastAnalyzer

__version__ = "1.0.0"
__all__ = [
    "CatPhanAnalyzer",
    "CTP404Analyzer",
    "UniformityAnalyzer",
    "HighContrastAnalyzer",
    "DICOMListener"
]
