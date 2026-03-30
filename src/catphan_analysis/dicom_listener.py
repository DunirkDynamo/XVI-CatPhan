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
from typing import Callable


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
        # Store the root listener directory and the managed subdirectories beneath it.
        self.base_path = Path(base_path)
        self.new_data_path = self.base_path / new_data_dir
        self.qa_path = self.base_path / qa_dir
        self.other_path = self.base_path / other_dir
        self.analysis_path = self.base_path / analysis_dir
        
        # Persist the polling cadence and stability threshold used by the receiver.
        self.sleep_interval = sleep_interval
        self.wait_cycles = wait_cycles
        
        # Track listener state and file-arrival stability between polling iterations.
        self.is_running = False
        self.file_count_old = 0
        self.wait_counter = 0
        self.step_counter = 0
        
        # Hold an optional callback that external code can use for notifications.
        self.analysis_callback = None
        
        # Ensure the managed directory tree exists before listening begins.
        self._create_directories()
    
    def _create_directories(self):
        """Create necessary directories if they don't exist."""
        # Create each managed directory so later file operations have a stable target.
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
        
        # Poll continuously until `stop()` flips the running flag.
        while self.is_running:
            self._check_and_process()
            time.sleep(self.sleep_interval)
            self.step_counter += 1
            
            # Emit an occasional heartbeat so long quiet periods still show activity.
            if self.step_counter % 10 == 0:
                print(f"Step {self.step_counter} - Monitoring...")
    
    def stop(self):
        """Stop the listener."""
        self.is_running = False
        print("DICOM Listener stopped.")
    
    def _check_and_process(self):
        """Check for new files and process if ready."""
        # Read the inbound directory contents; network-mounted paths may disappear temporarily.
        try:
            files = os.listdir(self.new_data_path)
        except Exception as e:
            print(f"Path not available: {e}")
            return
        
        # Collect supported incoming file types into separate lists for later handling.
        dicom_files = []
        prm_files = []
        
        for file in files:
            # Build the full source path for the current inbound file candidate.
            file_path = self.new_data_path / file
            
            # Remove directory-index artifacts that should never be processed as payload data.
            if file_path.is_file() and 'RTDIR.dir' in file:
                os.remove(file_path)
                continue
            
            # Classify normal DICOM payloads and legacy CT files that may lack a `.dcm` suffix.
            if file_path.is_file():
                try:
                    if pydicom.misc.is_dicom(file_path) or 'CT' in file.split('.')[0]:
                        # Remove stale `.dir` pseudo-files while retaining actual image payloads.
                        if 'CT' in file.split('.')[0] and file.split('.')[-1] == 'dir':
                            os.remove(file_path)
                        else:
                            dicom_files.append(file)
                except:
                    pass
                
                # Preserve `.prm` profile files so they move with the same study batch.
                if file.split('.')[-1] == 'prm':
                    prm_files.append(file)
        
        # Count all pending study files to determine whether arrival has stabilized.
        total_files = len(dicom_files) + len(prm_files)
        
        if total_files > 0:
            print(f"Found {len(dicom_files)} DICOM files, {len(prm_files)} PRM files")
        
        # Wait until the inbound file count stops growing before moving the study.
        if total_files > 0:
            if total_files > self.file_count_old:
                # A larger file count means the current study is still arriving.
                self.wait_counter = 1
                self.file_count_old = total_files
            elif total_files == self.file_count_old:
                # An unchanged count suggests the study may now be complete.
                self.wait_counter += 1
            
            # Transfer the study once the file count has remained stable long enough.
            if self.wait_counter >= self.wait_cycles:
                print("No new files received. Starting transfer...")
                self._transfer_and_flag(dicom_files, prm_files)
                
                # Reset the stability counters before the next inbound study.
                self.file_count_old = 0
                self.wait_counter = 0
    
    def _transfer_and_flag(self, dicom_files, prm_files):
        """
        Transfer files to appropriate directories and flag for analysis.
        
        Args:
            dicom_files: List of DICOM file names
            prm_files: List of .prm file names
        """
        # Build a timestamp suffix so each transferred study lands in a unique directory.
        timestamp = datetime.now().strftime("%d%b%Y_%H%M%S")
        
        # Group inbound files by patient or phantom identifier before transfer.
        file_groups = {}
        
        for file in dicom_files:
            # Build the source path for the current DICOM-like payload.
            file_path = self.new_data_path / file
            
            try:
                # Extract a grouping identifier from either legacy CT files or standard DICOM tags.
                if 'CT' in file.split('.')[0] and not file.split('.')[-1] == 'dcm':
                    # `ds` is the parsed DICOM dataset for a legacy-named CT image.
                    ds = pydicom.dcmread(file_path, force=True)
                    # `patient_id` is the normalized phantom identifier used for grouping.
                    patient_id = 'cat_' + ds.StationName
                else:
                    # `ds` is the parsed DICOM dataset for a normal incoming image.
                    ds = pydicom.dcmread(file_path)
                    # `patient_id` is the study grouping key read directly from DICOM metadata.
                    patient_id = ds.PatientID
                
                # Create the file list for a new identifier before appending to it.
                if patient_id not in file_groups:
                    file_groups[patient_id] = []
                file_groups[patient_id].append(file)
            except Exception as e:
                print(f"Error reading {file}: {e}")
        
        # Associate profile files with a synthetic identifier so they transfer with QA studies.
        for file in prm_files:
            # `patient_id` is the synthetic grouping key derived from the profile filename prefix.
            patient_id = file.split('_')[0] + 'prof'
            if patient_id not in file_groups:
                file_groups[patient_id] = []
            file_groups[patient_id].append(file)
        
        # Transfer each grouped study into its final destination folder.
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
        # Truncate and sanitize the identifier so it is safe to use in directory names.
        patient_id_clean = patient_id[:min(20, len(patient_id))]
        patient_id_clean = "".join(x for x in patient_id_clean if x.isalnum() or x in ['_', ' '])
        
        # Classify the study as QA or non-QA based on known phantom-related keywords.
        is_qa = any(keyword in patient_id.lower() for keyword in ['mlc', 'iso', 'prof', 'cat'])
        
        # Route the grouped files into the QA or non-QA tree.
        if is_qa:
            dest_dir = self.qa_path / f"{patient_id_clean}_{timestamp}"
        else:
            dest_dir = self.other_path / f"{patient_id_clean}_{timestamp}"
        
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        # Move each file into the chosen destination, normalizing extensions where needed.
        for file in files:
            # `src_path` is the original inbound file location.
            src_path = self.new_data_path / file
            
            # Append `.dcm` to legacy CT filenames that arrive without a medical-image suffix.
            if file.split('.')[-1] not in ['dcm', 'prm']:
                dest_file = dest_dir / (file + '.dcm')
            else:
                dest_file = dest_dir / file
            
            print(f"Transferring: {file} -> {dest_file}")
            shutil.move(src_path, dest_file)
        
        # Create an analysis flag only for QA studies, since those are the intended automated target.
        if is_qa:
            # `flag_file` is the sentinel file that tells the processor a study is ready.
            flag_file = self.analysis_path / f"{patient_id_clean}_{timestamp}"
            with open(flag_file, 'w') as f:
                f.write(f"{patient_id_clean}_{timestamp}")
            
            print(f"Flagged for analysis: {flag_file}")
            
            # Notify any registered callback that a new QA study has been staged.
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
        # Store the analyzer factory used to process each flagged study.
        self.analyzer_class = analyzer_class

        # Store the directory that contains sentinel files waiting to be processed.
        self.analysis_dir = Path(analysis_dir)
    
    def check_and_process(self):
        """
        Check for analysis flags and process any pending analyses.
        
        Returns:
            Number of analyses performed
        """
        # Track how many queued studies were successfully processed in this pass.
        count = 0
        
        # Exit early when the flag directory does not yet exist.
        if not self.analysis_dir.exists():
            return count
        
        # Walk each flag file and process the corresponding staged study.
        for flag_file in self.analysis_dir.iterdir():
            if flag_file.is_file():
                try:
                    # Read the target study directory name from the sentinel file.
                    with open(flag_file, 'r') as f:
                        # `dir_name` is the staged-study folder name referenced by the flag.
                        dir_name = f.read().strip()
                    
                    # Resolve the staged-study directory by checking the known destination roots.
                    data_path = self._find_data_path(dir_name)
                    
                    if data_path and data_path.exists():
                        print(f"\n{'='*60}")
                        print(f"Processing: {dir_name}")
                        print(f"{'='*60}\n")
                        
                        # Instantiate the analyzer and run the standard reporting workflow.
                        analyzer = self.analyzer_class(data_path)
                        analyzer.open_log()
                        analyzer.analyze()
                        analyzer.generate_report()
                        analyzer.close_log()
                        
                        count += 1
                    
                    # Remove the flag file so the same study is not processed twice.
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
        # `base` is the listener root that contains both QA and non-QA destination trees.
        base = self.analysis_dir.parent
        
        # Look for the study under the QA destination tree first.
        qa_path = base / 'dicomQA' / dir_name
        if qa_path.exists():
            return qa_path
        
        # Fall back to the non-QA destination tree if needed.
        other_path = base / 'dicomOTHER' / dir_name
        if other_path.exists():
            return other_path
        
        return None
