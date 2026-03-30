# Changelog

All notable changes to the CatPhan Analysis Package will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Reserved for changes after `v0.1.0`.

## [0.1.0] - 2026-03-30

### Added
- Initial public GitHub-ready release of the CatPhan analysis package.
- Modern `src`-layout package structure under `src/catphan_analysis`.
- Dynamic versioning with `setuptools-scm`, including generated package version metadata.
- Installable console entry points:
  - `catphan-analyze`
  - `catphan-select`
  - `catphan-listen`
- Packaged command-line, GUI, and listener entrypoints living inside the Python package.
- Windows executable build support via PyInstaller.
- Release automation to build and publish a Windows executable when a version tag is pushed.
- GitHub Pages automation to build and deploy the documentation site from version tags.
- Sphinx documentation site with autodoc, Napoleon, and Markdown support via `myst-parser`.
- Documentation sections for getting started, usage, reference material, development notes, executable packaging, and project background.
- Included project documents on the docs site, including the README, installation guide, quickstart guide, executable guide, and changelog.
- Alexandria-backed analyzers and plotters integrated into `CatPhanAnalyzer`.
- Detailed uniformity analysis and plot output through `CTP486_Detailed`.
- Broader package-level exports for the main orchestration, listener, and analyzer classes.

### Changed
- Reworked packaging metadata for publication, including project URLs, dependency declarations, optional extras, and console scripts.
- Switched dependency installation to the published Alexandria package name, `alexandria-project`.
- Moved executable build assets into dedicated project locations:
  - `packaging/pyinstaller/`
  - `scripts/`
- Removed duplicate root-level runtime entrypoints in favor of canonical package entrypoints.
- Reorganized repository documentation so GitHub-facing Markdown documents and Sphinx site content stay aligned.
- Updated docs configuration to derive documentation versions from Git tags.
- Restricted GitHub Pages deployment to version tags instead of every push.
- Standardized report generation and analyzer orchestration around the Alexandria-based workflow.
- Expanded package comments and docstrings for consistency with the project’s preferred documentation style.
- Improved package public API clarity in `catphan_analysis.__init__`.

### Fixed
- Editable install and package discovery issues related to the `src` layout.
- Version-file placement and version resolution issues for dynamic builds and installs.
- DICOM series sorting fallback now uses `ImagePositionPatient` or `InstanceNumber` when `SliceLocation` is missing.
- CTP404 location logic kept at `+30 mm` relative to CTP528.
- CTP486 location logic kept at `-80 mm` relative to CTP528.
- CTP528 slice selection uses the intended intelligent multi-slice selection workflow.
- Rotation and geometric helper comments/docs updated to match the current analyzer-driven implementation.
- Stale docstrings, unused imports, and minor API inconsistencies uncovered during the final polish pass.
- Virtual-environment ignore rules broadened so non-standard venv names are ignored across the repo.

### Validated
- Release workflow checks that the package version matches the pushed Git tag.
- Documentation deployment workflow is configured for tag-based GitHub Pages publishing.
- Updated package files were checked after the cleanup and polish passes with no editor-reported errors.
- The analysis package remains aligned with the validated CatPhan workflow already present in the project.

### Notes
- Version tags should use a semantic version format such as `v0.1.0`.
- GitHub Pages is intended to use GitHub Actions as its deployment source for this repository.

---

## Notes

### Version 0.1.0 - First packaged release
This release marks the first GitHub-ready packaged version of the project. It consolidates the repository cleanup, publishable packaging, documentation site setup, Windows executable workflow, and code/comment polish completed before the first public tag.

### Known Issues
- Legacy historical scripts and notes may still describe older pre-package layouts or earlier architectural stages.
- The legacy in-repo module implementations remain for reference/import compatibility, but the main analyzer flow now favors the Alexandria-backed analyzers.
