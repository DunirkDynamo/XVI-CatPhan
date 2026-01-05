"""
Example usage of the CatPhan Analysis package.

This script demonstrates various ways to use the package.
"""

from pathlib import Path
from catphan_analysis import CatPhanAnalyzer
from catphan_analysis.modules import CTP404Module, CTP486Module, CTP528Module


def example_basic_analysis():
    """
    Example: Basic complete analysis.
    """
    print("\n" + "="*60)
    print("Example 1: Basic Complete Analysis")
    print("="*60 + "\n")
    
    # Create analyzer
    analyzer = CatPhanAnalyzer(
        dicom_path='C:/TOH Data/CATPHAN',
        output_path='C:/TOH Data/CATPHAN/results'
    )
    
    # Run complete analysis
    analyzer.open_log()
    results = analyzer.analyze()
    report_path = analyzer.generate_report()
    analyzer.close_log()
    
    print(f"\nAnalysis complete! Report: {report_path}")


def example_step_by_step():
    """
    Example: Step-by-step analysis with access to intermediate results.
    """
    print("\n" + "="*60)
    print("Example 2: Step-by-Step Analysis")
    print("="*60 + "\n")
    
    # Create analyzer
    analyzer = CatPhanAnalyzer(dicom_path='C:/TOH Data/CATPHAN')
    
    # Load DICOM files
    num_files = analyzer.load_dicom_files()
    print(f"Loaded {num_files} DICOM files")
    
    # Locate modules
    indices = analyzer.locate_modules()
    print(f"\nModule locations:")
    for module, idx in indices.items():
        print(f"  {module}: slice {idx}")
    
    # Find centers
    centers = analyzer.find_module_centers()
    print(f"\nModule centers:")
    for module, center in centers.items():
        print(f"  {module}: ({center[0]:.1f}, {center[1]:.1f})")
    
    # Find rotation
    rotation = analyzer.find_rotation()
    print(f"\nRotation: {rotation:.2f} degrees")
    
    # Initialize and analyze modules
    analyzer.initialize_modules()
    
    # Analyze individual modules
    print("\n--- CTP404 Analysis ---")
    results_404 = analyzer.ctp404.analyze()
    print(f"Low Contrast Visibility: {results_404['low_contrast_visibility']:.3f}%")
    
    print("\n--- CTP486 Analysis ---")
    results_486 = analyzer.ctp486.analyze()
    print(f"Uniformity: {results_486['uniformity_percent']:.2f}%")
    
    print("\n--- CTP528 Analysis ---")
    results_528 = analyzer.ctp528.analyze()
    print(f"10% MTF: {results_528['mtf_10']:.3f} lp/mm")
    
    # Generate report
    analyzer.generate_report()


def example_individual_module():
    """
    Example: Using individual module classes directly.
    """
    print("\n" + "="*60)
    print("Example 3: Individual Module Analysis")
    print("="*60 + "\n")
    
    # First, need to load DICOM data
    analyzer = CatPhanAnalyzer(dicom_path='C:/TOH Data/CATPHAN')
    analyzer.load_dicom_files()
    analyzer.locate_modules()
    analyzer.find_module_centers()
    analyzer.find_rotation()
    
    # Now create individual module
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
    print(f"\nLow Contrast Visibility: {lcv:.3f}%")
    
    # Get summary
    summary = ctp404.get_results_summary()
    print("\nSummary:")
    for key, value in summary.items():
        print(f"  {key}: {value}")


def example_custom_workflow():
    """
    Example: Custom analysis workflow.
    """
    print("\n" + "="*60)
    print("Example 4: Custom Workflow")
    print("="*60 + "\n")
    
    # Create analyzer
    analyzer = CatPhanAnalyzer(
        dicom_path='C:/TOH Data/CATPHAN',
        catphan_model='500'
    )
    
    # Load data
    analyzer.load_dicom_files()
    
    # Custom filtering or preprocessing could go here
    # ...
    
    # Continue with analysis
    analyzer.locate_modules()
    analyzer.find_module_centers()
    analyzer.find_rotation()
    analyzer.initialize_modules()
    
    # Run analysis on only specific modules
    print("Analyzing CTP404 (contrast) only...")
    results_404 = analyzer.ctp404.analyze()
    
    # Custom post-processing
    for roi_data in results_404['contrast_rois']:
        roi_num, material, mean, std = roi_data
        if material == 'Air':
            print(f"Air ROI {roi_num}: {mean:.1f} HU (expected: ~-1000)")
        elif material == 'Water' or material == 'none':
            print(f"Water ROI {roi_num}: {mean:.1f} HU (expected: ~0)")
    
    # Generate custom report
    # ... your custom report generation code ...


def example_batch_processing():
    """
    Example: Batch processing multiple datasets.
    """
    print("\n" + "="*60)
    print("Example 5: Batch Processing")
    print("="*60 + "\n")
    
    # List of directories to process
    datasets = [
        'C:/TOH Data/CATPHAN/Dataset1',
        'C:/TOH Data/CATPHAN/Dataset2',
        'C:/TOH Data/CATPHAN/Dataset3',
    ]
    
    results_summary = []
    
    for dataset_path in datasets:
        if not Path(dataset_path).exists():
            print(f"Skipping {dataset_path} (not found)")
            continue
        
        print(f"\nProcessing: {dataset_path}")
        
        try:
            analyzer = CatPhanAnalyzer(dicom_path=dataset_path)
            analyzer.open_log()
            results = analyzer.analyze()
            analyzer.generate_report()
            analyzer.close_log()
            
            # Collect key metrics
            results_summary.append({
                'dataset': dataset_path,
                'uniformity': results['ctp486']['uniformity_percent'],
                'mtf_10': results['ctp528']['mtf_10']
            })
            
        except Exception as e:
            print(f"Error processing {dataset_path}: {e}")
    
    # Print summary
    print("\n" + "="*60)
    print("Batch Processing Summary")
    print("="*60)
    for result in results_summary:
        print(f"\n{result['dataset']}:")
        print(f"  Uniformity: {result['uniformity']:.2f}%")
        print(f"  10% MTF: {result['mtf_10']:.3f} lp/mm")


if __name__ == "__main__":
    print("\nCatPhan Analysis Package - Usage Examples")
    print("="*60)
    
    # Uncomment the example you want to run:
    
    # example_basic_analysis()
    # example_step_by_step()
    # example_individual_module()
    # example_custom_workflow()
    # example_batch_processing()
    
    print("\n\nNote: Update the paths in this script to match your data location.")
    print("Then uncomment the example you want to run.")
