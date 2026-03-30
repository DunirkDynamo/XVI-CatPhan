"""
Package-level CLI entrypoint for CatPhan analysis.

This lives inside the `catphan_analysis` package so it can be installed as a console script
(`catphan-analyze`) when the package is installed.
"""

import sys
import argparse
from pathlib import Path

from catphan_analysis import CatPhanAnalyzer


def main():
    """
    Run CatPhan analysis from the command line.

    Returns:
        Process exit code where `0` indicates success and `1` indicates failure.
    """
    # Create the top-level CLI parser for the batch-analysis workflow.
    parser = argparse.ArgumentParser(
        description='Analyze CatPhan phantom DICOM images',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze DICOM files in a directory
  catphan-analyze /path/to/dicom/files

  # Specify output directory
  catphan-analyze /path/to/dicom/files --output /path/to/output

  # Specify CatPhan model
  catphan-analyze /path/to/dicom/files --model 504
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

    # Parse user-provided CLI arguments into a simple namespace.
    args = parser.parse_args()

    # Convert the input directory string to a `Path` for filesystem checks.
    dicom_path = Path(args.dicom_path)

    # Validate the requested input location before starting the analysis.
    if not dicom_path.exists():
        print(f"Error: Path does not exist: {dicom_path}")
        return 1

    # Print a small banner so interactive command-line runs are easier to read.
    print("\n" + "="*60)
    print("CatPhan Analysis")
    print("="*60 + "\n")

    # Create the orchestrator object that will handle loading, analysis, and reporting.
    analyzer = CatPhanAnalyzer(
        dicom_path=dicom_path,
        output_path=args.output,
        catphan_model=args.model
    )

    try:
        # Open the analysis log before any substantial processing begins.
        analyzer.open_log()

        # Run the full CatPhan workflow.
        print("Starting analysis...")
        analyzer.analyze()

        # Generate the user-facing report once the analysis results exist.
        print("\nGenerating report...")
        report_path = analyzer.generate_report(include_plots=not args.no_plots)

        print(f"\nAnalysis complete!")
        print(f"Report saved to: {report_path}")

        # Close the log cleanly on the success path.
        analyzer.close_log()
        return 0

    except Exception as e:
        # Surface the failure in a user-visible way and include a traceback for debugging.
        print(f"\nError during analysis: {e}")
        import traceback
        traceback.print_exc()

        # Attempt to close the log even when the workflow fails partway through.
        try:
            analyzer.close_log()
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    sys.exit(main())
