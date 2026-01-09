# Changelog

All notable changes to the CatPhan Analysis Package will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-01-09

### Added
- Complete refactoring from procedural scripts to object-oriented architecture
- `CatPhanAnalyzer` executive class for coordinating analysis workflow
- Modular analysis classes: `CTP404Module`, `CTP486Module`, `CTP528Module`
- Utility classes: `CatPhanGeometry`, `SliceLocator`, `ImageProcessor`
- Three usage modes:
  - GUI folder selection (`select_and_analyze.py` / `catphan-select`)
  - Command-line analysis (`main.py` / `catphan-analyze`)
  - Automated DICOM listener (`listen_and_analyze.py` / `catphan-listen`)
- Console entry points for easy installation: `catphan-select`, `catphan-analyze`, `catphan-listen`
- Comprehensive documentation:
  - `HOW_TO_USE.md` - User guide for all three usage modes
  - `README.md` - Package overview and features
  - `QUICK_REFERENCE.md` - Quick reference for classes and methods
  - `CLASS_ARCHITECTURE.md` - Architecture and design patterns
  - `REFACTORING_SUMMARY.md` - Detailed refactoring documentation
- Line pair profile visualization in output plots
- Color-coded ROI overlays for uniformity module
- Sphinx documentation structure with auto-generated API reference

### Changed
- Rotation calculation now properly converts 58.5mm ring radius from mm to pixels
- CTP528 slice selection uses intelligent 3-slice averaging algorithm
- CTP404 module location corrected to +30mm (not -30mm) from CTP528
- Array boolean checks updated to `is not None` pattern to avoid numpy warnings
- Slice selection moved from `CTP528Module` to `CatPhanGeometry` utilities (architectural improvement)
- North/South ROI labels corrected for image coordinate system (Y increases downward)
- Uniformity module uses proper numpy indexing `[y, x]` consistently

### Fixed
- Second line pair angle corrected from 38° to 40° for accurate MTF calculation
- South ROI mask bug in original code (was using north mask) - fixed in refactored version
- Scaling points preservation for green crosshair visualization
- CTP528 center finding now uses intelligent slice selection instead of fixed offset

### Validated
- All numerical results match reference implementation (processDICOMcat2.py)
- CTP404: Contrast, HU accuracy, spatial scaling, slice thickness - ✓ Verified
- CTP486: Uniformity (all 5 regions) - ✓ Verified  
- CTP528: MTF values at 10%, 30%, 50%, 80% - ✓ Verified

### Reference Values (from processDICOMcat2.py)
- CTP528 expected slice: 60
- CTP528 detection thresholds: thres1=100, thres2=50
- CTP486 distance: -80mm from CTP528
- CTP404 distance: +30mm from CTP528
- No +2048 interpolation offset

## [Unreleased]

### Future Enhancements
- CatPhan-600 support
- Additional phantom models
- PDF report generation
- Database integration for trending
- REST API for remote analysis
- DICOM-SR structured reporting

---

## Notes

### Version 1.0.0 - Production Release
This release represents a complete, validated refactoring of the original procedural scripts into a professional, maintainable package. All algorithms have been verified against the reference implementation to ensure numerical accuracy while providing improved code organization and extensibility.

### Known Issues
- Original processDICOMcat.py contains bugs in uniformity module (South ROI uses wrong mask, East/West have inconsistent indexing). These bugs are **not** reproduced in the refactored version, which uses correct indexing throughout.
