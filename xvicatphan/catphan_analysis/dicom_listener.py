"""
DICOM Listener and Processor

Handles automated DICOM file reception and triggers analysis.
"""

import os
import time
import shutil
import pydicom
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable


class DICOMListener:
    """
    Listens for DICOM files and processes them automatically.
    
    This class monitors a directory for incoming DICOM files,
    organizes them by patient/phantom ID, and triggers analysis.
    """
    
    def __init__(self, 
                 base_path,
                 new_data_dir='newdata',
                 qa_dir='dicomQA',
                 other_dir='dicomOTHER',
                 analysis_dir='toanalyze',
                 sleep_interval=5,
                 wait_cycles=8):
        """
        Initialize DICOM listener.
        
        Args:
            base_path: Base directory for DICOM operations
            new_data_dir: Subdirectory where new files arrive
            qa_dir: Subdirectory for QA phantoms
            other_dir: Subdirectory for non-QA scans
            analysis_dir: Subdirectory with analysis flags
            sleep_interval: Seconds to wait between checks
            wait_cycles: Number of cycles to wait after last file before processing
        """
        self.base_path = Path(base_path)
        self.new_data_path = self.base_path / new_data_dir
        self.qa_path = self.base_path / qa_dir
        self.other_path = self.base_path / other_dir
        self.analysis_path = self.base_path / analysis_dir
        
        self.sleep_interval = sleep_interval
        self.wait_cycles = wait_cycles
        
        self.is_running = False
        self.file_count_old = 0
        self.wait_counter = 0
        self.step_counter = 0
        
        # Callback for custom processing
        self.analysis_callback = None
        
        # Ensure directories exist
        self._create_directories()
    
    def _create_directories(self):
        """Create necessary directories if they don't exist."""
        for path in [self.new_data_path, self.qa_path, self.other_path, self.analysis_path]:
            path.mkdir(parents=True, exist_ok=True)
    
    def set_analysis_callback(self, callback: Callable[[Path], None]):
        """
        Set a callback function to be called when files are ready for analysis.
        
        Args:
            callback: Function that takes a Path argument (folder to analyze)
        """
        self.analysis_callback = callback
    
    def start(self):
        """
        Start listening for DICOM files.
        
        Runs in a loop until stopped.
        """
        self.is_running = True
        print(f"DICOM Listener started. Monitoring: {self.new_data_path}")
        print(f"Check interval: {self.sleep_interval} seconds")
        print(f"Wait cycles: {self.wait_cycles}")
        
        while self.is_running:
            self._check_and_process()
            time.sleep(self.sleep_interval)
            self.step_counter += 1
            
            if self.step_counter % 10 == 0:
                print(f"Step {self.step_counter} - Monitoring...")
    
    def stop(self):
        """Stop the listener."""
        self.is_running = False
        print("DICOM Listener stopped.")
    
    def _check_and_process(self):
        """Check for new files and process if ready."""
        # Check if path is available
        try:
            files = os.listdir(self.new_data_path)
        except Exception as e:
            print(f"Path not available: {e}")
            return
        
        # Filter for DICOM files
        dicom_files = []
        prm_files = []
        
        for file in files:
            file_path = self.new_data_path / file
            
            # Remove RTDIR files
            if file_path.is_file() and 'RTDIR.dir' in file:
                os.remove(file_path)
                continue
            
            # Check for DICOM files
            if file_path.is_file():
                try:
                    if pydicom.misc.is_dicom(file_path) or 'CT' in file.split('.')[0]:
                        # Remove .dir files
                        if 'CT' in file.split('.')[0] and file.split('.')[-1] == 'dir':
                            os.remove(file_path)
                        else:
                            dicom_files.append(file)
                except:
                    pass
                
                # Check for .prm files
                if file.split('.')[-1] == 'prm':
                    prm_files.append(file)
        
        total_files = len(dicom_files) + len(prm_files)
        
        if total_files > 0:
            print(f"Found {len(dicom_files)} DICOM files, {len(prm_files)} PRM files")
        
        # Check if files are still being received
        if total_files > 0:
            if total_files > self.file_count_old:
                # New files received
                self.wait_counter = 1
                self.file_count_old = total_files
            elif total_files == self.file_count_old:
                # No new files, increment wait counter
                self.wait_counter += 1
            
            # Process if we've waited long enough
            if self.wait_counter >= self.wait_cycles:
                print("No new files received. Starting transfer...")
                self._transfer_and_flag(dicom_files, prm_files)
                
                # Reset counters
                self.file_count_old = 0
                self.wait_counter = 0
    
    def _transfer_and_flag(self, dicom_files, prm_files):
        """
        Transfer files to appropriate directories and flag for analysis.
        
        Args:
            dicom_files: List of DICOM file names
            prm_files: List of .prm file names
        """
        timestamp = datetime.now().strftime("%d%b%Y_%H%M%S")
        
        # Group files by patient ID
        file_groups = {}
        
        for file in dicom_files:
            file_path = self.new_data_path / file
            
            try:
                # Read patient ID
                if 'CT' in file.split('.')[0] and not file.split('.')[-1] == 'dcm':
                    ds = pydicom.dcmread(file_path, force=True)
                    patient_id = 'cat_' + ds.StationName
                else:
                    ds = pydicom.dcmread(file_path)
                    patient_id = ds.PatientID
                
                if patient_id not in file_groups:
                    file_groups[patient_id] = []
                file_groups[patient_id].append(file)
            except Exception as e:
                print(f"Error reading {file}: {e}")
        
        # Handle .prm files
        for file in prm_files:
            patient_id = file.split('_')[0] + 'prof'
            if patient_id not in file_groups:
                file_groups[patient_id] = []
            file_groups[patient_id].append(file)
        
        # Transfer each group
        for patient_id, files in file_groups.items():
            self._transfer_group(patient_id, files, timestamp)
    
    def _transfer_group(self, patient_id, files, timestamp):
        """
        Transfer a group of files for one patient/phantom.
        
        Args:
            patient_id: Patient or phantom ID
            files: List of files to transfer
            timestamp: Timestamp string for directory naming
        """
        # Clean patient ID
        patient_id_clean = patient_id[:min(20, len(patient_id))]
        patient_id_clean = "".join(x for x in patient_id_clean if x.isalnum() or x in ['_', ' '])
        
        # Determine destination
        is_qa = any(keyword in patient_id.lower() for keyword in ['mlc', 'iso', 'prof', 'cat'])
        
        if is_qa:
            dest_dir = self.qa_path / f"{patient_id_clean}_{timestamp}"
        else:
            dest_dir = self.other_path / f"{patient_id_clean}_{timestamp}"
        
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        # Transfer files
        for file in files:
            src_path = self.new_data_path / file
            
            # Add .dcm extension if needed
            if file.split('.')[-1] not in ['dcm', 'prm']:
                dest_file = dest_dir / (file + '.dcm')
            else:
                dest_file = dest_dir / file
            
            print(f"Transferring: {file} -> {dest_file}")
            shutil.move(src_path, dest_file)
        
        # Flag for analysis if QA
        if is_qa:
            flag_file = self.analysis_path / f"{patient_id_clean}_{timestamp}"
            with open(flag_file, 'w') as f:
                f.write(f"{patient_id_clean}_{timestamp}")
            
            print(f"Flagged for analysis: {flag_file}")
            
            # Trigger callback if set
            if self.analysis_callback:
                try:
                    self.analysis_callback(dest_dir)
                except Exception as e:
                    print(f"Error in analysis callback: {e}")


class DICOMProcessor:
    """
    Processes DICOM files flagged for analysis.
    
    Works with DICOMListener to automatically analyze incoming data.
    """
    
    def __init__(self, analyzer_class, analysis_dir):
        """
        Initialize DICOM processor.
        
        Args:
            analyzer_class: The CatPhanAnalyzer class (or similar)
            analysis_dir: Directory containing analysis flags
        """
        self.analyzer_class = analyzer_class
        self.analysis_dir = Path(analysis_dir)
    
    def check_and_process(self):
        """
        Check for analysis flags and process any pending analyses.
        
        Returns:
            Number of analyses performed
        """
        count = 0
        
        # Look for flag files
        if not self.analysis_dir.exists():
            return count
        
        for flag_file in self.analysis_dir.iterdir():
            if flag_file.is_file():
                try:
                    # Read the directory name from flag
                    with open(flag_file, 'r') as f:
                        dir_name = f.read().strip()
                    
                    # Determine the full path (check both QA and OTHER directories)
                    data_path = self._find_data_path(dir_name)
                    
                    if data_path and data_path.exists():
                        print(f"\n{'='*60}")
                        print(f"Processing: {dir_name}")
                        print(f"{'='*60}\n")
                        
                        # Run analysis
                        analyzer = self.analyzer_class(data_path)
                        analyzer.open_log()
                        analyzer.analyze()
                        analyzer.generate_report()
                        analyzer.close_log()
                        
                        count += 1
                    
                    # Remove flag file
                    flag_file.unlink()
                    
                except Exception as e:
                    print(f"Error processing {flag_file}: {e}")
        
        return count
    
    def _find_data_path(self, dir_name):
        """
        Find the full path to the data directory.
        
        Args:
            dir_name: Directory name from flag file
            
        Returns:
            Path to data directory or None
        """
        base = self.analysis_dir.parent
        
        # Check QA directory
        qa_path = base / 'dicomQA' / dir_name
        if qa_path.exists():
            return qa_path
        
        # Check OTHER directory
        other_path = base / 'dicomOTHER' / dir_name
        if other_path.exists():
            return other_path
        
        return None
