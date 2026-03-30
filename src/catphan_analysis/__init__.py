"""
CatPhan Analysis Package

A professional software package for analyzing CatPhan phantom DICOM images.
Provides modular, class-based analysis of CTP404, CTP486, and CTP528 modules.
"""

from importlib.metadata import PackageNotFoundError, version as get_version

# Re-export the primary orchestration and automation classes at package scope.
from .analyzer import CatPhanAnalyzer
from .dicom_listener import DICOMListener, DICOMProcessor

# Re-export the Alexandria-backed analyzers commonly used by downstream callers.
from alexandria import CTP404Analyzer, UniformityAnalyzer, HighContrastAnalyzer

try:
    # Prefer the version written by `setuptools-scm` during builds and installs.
    from ._version import version as __version__
except ImportError:
    try:
        # Fall back to installed package metadata when the generated file is unavailable.
        __version__ = get_version("catphan-analysis")
    except PackageNotFoundError:
        # Use a safe placeholder during source-only execution without installed metadata.
        __version__ = "0.0.0"

# Publish the package's supported public API surface.
__all__ = [
    "__version__",
    "CatPhanAnalyzer",
    "CTP404Analyzer",
    "UniformityAnalyzer",
    "HighContrastAnalyzer",
    "DICOMListener",
    "DICOMProcessor",
]
