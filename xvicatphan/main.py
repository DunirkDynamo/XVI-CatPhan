"""
Main entry point for CatPhan analysis.

This script can be run directly to analyze CatPhan phantom DICOM images.
"""

import sys
import argparse
from pathlib import Path

from catphan_analysis import CatPhanAnalyzer


def main():
    """
    Main function for command-line usage.
    """
    parser = argparse.ArgumentParser(
        description='Analyze CatPhan phantom DICOM images',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze DICOM files in a directory
  python main.py /path/to/dicom/files

  # Specify output directory
  python main.py /path/to/dicom/files --output /path/to/output

  # Specify CatPhan model
  python main.py /path/to/dicom/files --model 504
        """
    )
    
    parser.add_argument(
        'dicom_path',
        type=str,
        help='Path to directory containing DICOM files'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        default=None,
        help='Output directory for results (default: same as input)'
    )
    
    parser.add_argument(
        '--model', '-m',
        type=str,
        default='500',
        choices=['500', '504'],
        help='CatPhan model (default: 500)'
    )
    
    parser.add_argument(
        '--no-plots',
        action='store_true',
        help='Skip plot generation'
    )
    
    args = parser.parse_args()
    
    # Validate input path
    dicom_path = Path(args.dicom_path)
    if not dicom_path.exists():
        print(f"Error: Path does not exist: {dicom_path}")
        return 1
    
    # Create analyzer
    print("\n" + "="*60)
    print("CatPhan Analysis")
    print("="*60 + "\n")
    
    analyzer = CatPhanAnalyzer(
        dicom_path=dicom_path,
        output_path=args.output,
        catphan_model=args.model
    )
    
    try:
        # Open log file
        analyzer.open_log()
        
        # Run analysis
        print("Starting analysis...")
        results = analyzer.analyze()
        
        # Generate report
        print("\nGenerating report...")
        report_path = analyzer.generate_report(include_plots=not args.no_plots)
        
        print(f"\nAnalysis complete!")
        print(f"Report saved to: {report_path}")
        
        # Close log
        analyzer.close_log()
        
        return 0
        
    except Exception as e:
        print(f"\nError during analysis: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
