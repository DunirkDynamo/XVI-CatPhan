"""
Entry point for automated DICOM listening and processing.

This script runs the DICOM listener that monitors for incoming files
and automatically triggers analysis.
"""

import sys
import argparse
from pathlib import Path

from catphan_analysis import CatPhanAnalyzer, DICOMListener
from catphan_analysis.dicom_listener import DICOMProcessor


def main():
    """
    Main function for DICOM listener service.
    """
    parser = argparse.ArgumentParser(
        description='Run DICOM listener for automated CatPhan analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run listener with default settings
  python listen_and_analyze.py /path/to/dicom/receiver

  # Custom check interval
  python listen_and_analyze.py /path/to/dicom/receiver --interval 10

  # Custom wait cycles
  python listen_and_analyze.py /path/to/dicom/receiver --wait-cycles 5
        """
    )
    
    parser.add_argument(
        'base_path',
        type=str,
        help='Base path for DICOM receiver (should contain newdata subdirectory)'
    )
    
    parser.add_argument(
        '--interval', '-i',
        type=int,
        default=5,
        help='Check interval in seconds (default: 5)'
    )
    
    parser.add_argument(
        '--wait-cycles', '-w',
        type=int,
        default=8,
        help='Number of cycles to wait before processing (default: 8)'
    )
    
    args = parser.parse_args()
    
    # Validate base path
    base_path = Path(args.base_path)
    if not base_path.exists():
        print(f"Error: Path does not exist: {base_path}")
        print("Creating directory...")
        base_path.mkdir(parents=True, exist_ok=True)
    
    print("\n" + "="*60)
    print("CatPhan DICOM Listener and Analyzer")
    print("="*60 + "\n")
    print(f"Base path: {base_path}")
    print(f"Check interval: {args.interval} seconds")
    print(f"Wait cycles: {args.wait_cycles}")
    print("\nPress Ctrl+C to stop\n")
    
    # Create listener
    listener = DICOMListener(
        base_path=base_path,
        sleep_interval=args.interval,
        wait_cycles=args.wait_cycles
    )
    
    # Set up processor
    processor = DICOMProcessor(
        analyzer_class=CatPhanAnalyzer,
        analysis_dir=listener.analysis_path
    )
    
    # Set callback to trigger processing
    def analyze_callback(data_path):
        """Called when files are ready for analysis."""
        print(f"\nTriggering analysis for: {data_path}")
    
    listener.set_analysis_callback(analyze_callback)
    
    # Start listener
    try:
        # Run listener
        listener.start()
        
    except KeyboardInterrupt:
        print("\n\nStopping listener...")
        listener.stop()
        
        # Process any remaining flagged analyses
        print("Processing remaining analyses...")
        count = processor.check_and_process()
        print(f"Processed {count} analyses")
        
        print("\nShutdown complete.")
        return 0
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
