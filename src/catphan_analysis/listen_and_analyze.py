"""
Entry point for automated DICOM listening and processing.

This script runs the DICOM listener that monitors for incoming files
and automatically triggers analysis.
"""

import sys
import argparse
from pathlib import Path

from catphan_analysis.analyzer import CatPhanAnalyzer
from catphan_analysis.dicom_listener import DICOMListener, DICOMProcessor


def main():
    """
    Run the long-lived DICOM listener service.

    Returns:
        Process exit code where `0` indicates clean shutdown and `1` indicates failure.
    """
    # Create the CLI parser for the background listener workflow.
    parser = argparse.ArgumentParser(
        description='Run DICOM listener for automated CatPhan analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run listener with default settings
  python -m catphan_analysis.listen_and_analyze /path/to/dicom/receiver

  # Custom check interval
  python -m catphan_analysis.listen_and_analyze /path/to/dicom/receiver --interval 10

  # Custom wait cycles
  python -m catphan_analysis.listen_and_analyze /path/to/dicom/receiver --wait-cycles 5
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
    
    # Parse command-line options into a simple namespace object.
    args = parser.parse_args()
    
    # Convert the listener root to a `Path` and ensure it exists.
    base_path = Path(args.base_path)
    if not base_path.exists():
        print(f"Error: Path does not exist: {base_path}")
        print("Creating directory...")
        base_path.mkdir(parents=True, exist_ok=True)
    
    # Print the runtime configuration so operator errors are obvious at startup.
    print("\n" + "="*60)
    print("CatPhan DICOM Listener and Analyzer")
    print("="*60 + "\n")
    print(f"Base path: {base_path}")
    print(f"Check interval: {args.interval} seconds")
    print(f"Wait cycles: {args.wait_cycles}")
    print("\nPress Ctrl+C to stop\n")
    
    # Create the directory-monitoring service.
    listener = DICOMListener(
        base_path=base_path,
        sleep_interval=args.interval,
        wait_cycles=args.wait_cycles
    )
    
    # Create the deferred processor that will consume any queued analysis flags.
    processor = DICOMProcessor(
        analyzer_class=CatPhanAnalyzer,
        analysis_dir=listener.analysis_path
    )
    
    # Register a lightweight callback so incoming-study events are visible in the console.
    def analyze_callback(data_path):
        """Log when a transferred study is ready for downstream analysis."""
        print(f"\nTriggering analysis for: {data_path}")
    
    listener.set_analysis_callback(analyze_callback)
    
    # Start the long-running listener loop and keep handling shutdown paths cleanly.
    try:
        listener.start()
        
    except KeyboardInterrupt:
        print("\n\nStopping listener...")
        listener.stop()
        
        # Drain any analysis flags that were created before the operator stopped the service.
        print("Processing remaining analyses...")
        processed_count = processor.check_and_process()
        print(f"Processed {processed_count} analyses")
        
        print("\nShutdown complete.")
        return 0
        
    except Exception as e:
        # Print the traceback so unexpected listener failures are diagnosable.
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
