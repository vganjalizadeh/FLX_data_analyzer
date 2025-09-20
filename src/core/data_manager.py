import pandas as pd
import h5py
import zipfile
import json
import uuid
import os
import numpy as np
from pathlib import Path
from datetime import datetime
from PIL import Image
import io
import logging

# Set up logging with proper formatting
def setup_logger():
    """Set up a properly formatted logger for DataManager."""
    logger = logging.getLogger('DataManager')
    logger.setLevel(logging.INFO)
    
    # Remove any existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create console handler with formatting
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Create detailed formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(name)s | %(levelname)-8s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    logger.propagate = False  # Prevent duplicate logs
    
    return logger

# Initialize the logger
logger = setup_logger()

class DataManager:
    """
    FLDB Database Manager for handling FLZ, FLR, and FLB files.
    
    Database Structure (HDF5):
    /
    ├── metadata/
    │   ├── db_info          # Database metadata
    │   └── file_index       # Index of all files in database
    └── files/
        └── {unique_id}/     # Unique folder for each file
            ├── metadata/    # File metadata (from metadata.json)
            ├── raw_data/    # Raw data (images, photon data)
            │   ├── alignment_image
            │   ├── laser_on_image
            │   └── photon_data
            └── analysis/    # Analysis results (added when processed)
                ├── {analysis_id}/
                │   ├── results
                │   └── metadata
    """
    
    def __init__(self, log_file=None, log_level=logging.INFO):
        self.db_path = None
        self.db_file = None
        
        # Configure logging for this instance
        self._setup_logging(log_file, log_level)
        
        # Create or open default database
        self._initialize_default_database()
        
    def _setup_logging(self, log_file=None, log_level=logging.INFO):
        """Configure logging for this DataManager instance."""
        global logger
        logger.setLevel(log_level)
        
        # Add file handler if log_file is specified
        if log_file:
            # Create file handler
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(log_level)
            
            # Create formatter for file logs (more detailed)
            file_formatter = logging.Formatter(
                fmt='%(asctime)s | %(name)s | %(levelname)-8s | %(filename)s:%(funcName)s:%(lineno)d | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            
            # Add file handler to logger
            logger.addHandler(file_handler)
            logger.info(f"File logging enabled: {log_file}")
    
    @staticmethod
    def set_logging_level(level):
        """Set the logging level for all DataManager instances.
        
        Args:
            level: logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL
        """
        global logger
        logger.setLevel(level)
        for handler in logger.handlers:
            handler.setLevel(level)
        logger.info(f"Logging level changed to: {logging.getLevelName(level)}")
    
    @staticmethod
    def configure_logging_format(simple=False):
        """Configure logging format to be simple or detailed.
        
        Args:
            simple (bool): If True, use simple format. If False, use detailed format.
        """
        global logger
        
        if simple:
            formatter = logging.Formatter(
                fmt='%(levelname)s: %(message)s'
            )
        else:
            formatter = logging.Formatter(
                fmt='%(asctime)s | %(name)s | %(levelname)-8s | %(funcName)s:%(lineno)d | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        
        # Update all handlers
        for handler in logger.handlers:
            handler.setFormatter(formatter)
        
        format_type = "simple" if simple else "detailed"
        logger.info(f"Logging format set to: {format_type}")
    
    def _initialize_default_database(self):
        """Initialize a default database if none exists."""
        try:
            import os
            # Create default database in the current directory
            default_db_path = os.path.join(os.getcwd(), 'flx_data.fldb')
            
            if os.path.exists(default_db_path):
                # Open existing database
                self.open_database(default_db_path)
                logger.info(f"Opened existing default database: {default_db_path}")
            else:
                # Create new database
                self.create_database(default_db_path)
                self.open_database(default_db_path)
                logger.info(f"Created new default database: {default_db_path}")
                
        except Exception as e:
            logger.error(f"Failed to initialize default database: {e}")
        
    def create_database(self, db_path):
        """Create a new FLDB database."""
        logger.debug(f"Creating database at: {db_path}")
        try:
            self.db_path = db_path
            if not db_path.endswith('.fldb'):
                db_path += '.fldb'
                logger.debug(f"Added .fldb extension: {db_path}")
                
            logger.debug("Initializing HDF5 file structure")
            with h5py.File(db_path, 'w') as f:
                # Create main structure
                metadata_group = f.create_group('metadata')
                files_group = f.create_group('files')
                logger.debug("Created main group structure: metadata/, files/")
                
                # Database metadata
                db_info = {
                    'created': datetime.now().isoformat(),
                    'version': '1.0',
                    'description': 'FLX Data Analyzer Database'
                }
                metadata_group.create_dataset('db_info', data=json.dumps(db_info))
                logger.debug("Added database metadata")
                
                # File index (will store list of file IDs and their info)
                metadata_group.create_dataset('file_index', data=json.dumps({}))
                logger.debug("Initialized empty file index")
                
            logger.info(f"Successfully created FLDB database: {db_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create database '{db_path}': {e}")
            return False
    
    def open_database(self, db_path):
        """Open an existing FLDB database."""
        logger.debug(f"Attempting to open database: {db_path}")
        try:
            if not os.path.exists(db_path):
                logger.error(f"Database file not found: {db_path}")
                return False
                
            logger.debug("File exists, checking structure")
            self.db_path = db_path
            # Test opening the file
            with h5py.File(db_path, 'r') as f:
                if 'metadata' not in f or 'files' not in f:
                    logger.error("Invalid FLDB file structure - missing required groups")
                    return False
                
                # Log database info if available
                if 'db_info' in f['metadata']:
                    db_info = json.loads(f['metadata']['db_info'][()])
                    logger.debug(f"Database version: {db_info.get('version', 'unknown')}")
                    logger.debug(f"Created: {db_info.get('created', 'unknown')}")
                    
            logger.info(f"Successfully opened FLDB database: {db_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to open database '{db_path}': {e}")
            return False
    
    def add_flz_file(self, flz_path):
        """Add a FLZ file to the database."""
        logger.debug(f"Adding FLZ file: {flz_path}")
        try:
            if not self.db_path:
                logger.error("Cannot add file: No database is currently opened")
                return None
                
            if not os.path.exists(flz_path):
                logger.error(f"FLZ file not found: {flz_path}")
                return None
                
            unique_id = str(uuid.uuid4())
            logger.debug(f"Generated unique ID for file: {unique_id}")
            
            logger.debug("Extracting FLZ file contents")
            with zipfile.ZipFile(flz_path, 'r') as zip_file:
                # Extract file contents
                file_data = self._extract_flz_contents(zip_file)
                
            logger.debug(f"Extracted data - Images: {file_data['alignment_image'] is not None}, "
                        f"{file_data['laser_on_image'] is not None}, "
                        f"Photon data: {file_data['photon_data'] is not None}")
                
            # Add to database
            with h5py.File(self.db_path, 'a') as f:
                file_group = f['files'].create_group(unique_id)
                
                # Store metadata
                metadata_group = file_group.create_group('metadata')
                if file_data['metadata']:
                    metadata_group.create_dataset('file_metadata', data=json.dumps(file_data['metadata']))
                
                # Store raw data
                raw_group = file_group.create_group('raw_data')
                
                # Store images
                if file_data['alignment_image'] is not None:
                    raw_group.create_dataset('alignment_image', data=file_data['alignment_image'],
                                            compression='gzip', compression_opts=6)
                else:
                    raw_group.create_dataset('alignment_image', data=json.dumps(None))
                    
                if file_data['laser_on_image'] is not None:
                    raw_group.create_dataset('laser_on_image', data=file_data['laser_on_image'],
                                            compression='gzip', compression_opts=6)
                else:
                    raw_group.create_dataset('laser_on_image', data=json.dumps(None))
                
                # Store photon data
                if file_data['photon_data'] is not None:
                    raw_group.create_dataset('photon_data', data=file_data['photon_data'], 
                                            compression='gzip', compression_opts=6)
                else:
                    raw_group.create_dataset('photon_data', data=json.dumps(None))
                
                # Create empty analysis group
                file_group.create_group('analysis')
                
                # Update file index
                self._update_file_index(unique_id, {
                    'original_path': flz_path,
                    'file_type': 'flz',
                    'added': datetime.now().isoformat(),
                    'has_alignment_image': file_data['alignment_image'] is not None,
                    'has_laser_on_image': file_data['laser_on_image'] is not None,
                    'has_photon_data': file_data['photon_data'] is not None
                })
            
            logger.info(f"Successfully added FLZ file '{os.path.basename(flz_path)}' with ID: {unique_id}")
            return unique_id
            
        except zipfile.BadZipFile as e:
            logger.error(f"Invalid ZIP file '{flz_path}': {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to add FLZ file '{flz_path}': {e}")
            return None
    
    def add_flr_file(self, flr_path):
        """Add a FLR file to the database (raw photon data only)."""
        try:
            if not self.db_path:
                logger.error("No database opened")
                return None
                
            unique_id = str(uuid.uuid4())
            
            # Load FLR data (assuming it's binary photon data)
            with open(flr_path, 'rb') as f:
                photon_data = np.frombuffer(f.read(), dtype=np.uint8)
            
            # Add to database with template structure
            with h5py.File(self.db_path, 'a') as f:
                file_group = f['files'].create_group(unique_id)
                
                # Store minimal metadata
                metadata_group = file_group.create_group('metadata')
                file_metadata = {
                    'original_filename': os.path.basename(flr_path),
                    'file_type': 'flr',
                    'imported': datetime.now().isoformat()
                }
                metadata_group.create_dataset('file_metadata', data=json.dumps(file_metadata))
                
                # Store raw data with template structure
                raw_group = file_group.create_group('raw_data')
                raw_group.create_dataset('alignment_image', data=json.dumps(None))  # No image data
                raw_group.create_dataset('laser_on_image', data=json.dumps(None))   # No image data
                raw_group.create_dataset('photon_data', data=photon_data)
                
                # Create empty analysis group
                file_group.create_group('analysis')
                
                # Update file index
                self._update_file_index(unique_id, {
                    'original_path': flr_path,
                    'file_type': 'flr',
                    'added': datetime.now().isoformat(),
                    'has_alignment_image': False,
                    'has_laser_on_image': False,
                    'has_photon_data': True
                })
            
            logger.info(f"Added FLR file to database with ID: {unique_id}")
            return unique_id
            
        except Exception as e:
            logger.error(f"Error adding FLR file: {e}")
            return None
    
    def add_flb_file(self, flb_path):
        """Add a FLB file to the database (similar to FLR)."""
        try:
            if not self.db_path:
                logger.error("No database opened")
                return None
                
            unique_id = str(uuid.uuid4())
            
            # Load FLB data (assuming it's binary data)
            with open(flb_path, 'rb') as f:
                raw_data = np.frombuffer(f.read(), dtype=np.uint8)
            
            # Add to database with template structure
            with h5py.File(self.db_path, 'a') as f:
                file_group = f['files'].create_group(unique_id)
                
                # Store minimal metadata
                metadata_group = file_group.create_group('metadata')
                file_metadata = {
                    'original_filename': os.path.basename(flb_path),
                    'file_type': 'flb',
                    'imported': datetime.now().isoformat()
                }
                metadata_group.create_dataset('file_metadata', data=json.dumps(file_metadata))
                
                # Store raw data with template structure
                raw_group = file_group.create_group('raw_data')
                raw_group.create_dataset('alignment_image', data=json.dumps(None))  # No image data
                raw_group.create_dataset('laser_on_image', data=json.dumps(None))   # No image data
                raw_group.create_dataset('photon_data', data=raw_data)
                
                # Create empty analysis group
                file_group.create_group('analysis')
                
                # Update file index
                self._update_file_index(unique_id, {
                    'original_path': flb_path,
                    'file_type': 'flb',
                    'added': datetime.now().isoformat(),
                    'has_alignment_image': False,
                    'has_laser_on_image': False,
                    'has_photon_data': True
                })
            
            logger.info(f"Added FLB file to database with ID: {unique_id}")
            return unique_id
            
        except Exception as e:
            logger.error(f"Error adding FLB file: {e}")
            return None
    
    def add_analysis_result(self, file_id, analysis_data, analysis_metadata=None):
        """Add analysis results for a specific file."""
        try:
            if not self.db_path:
                logger.error("No database opened")
                return None
                
            analysis_id = str(uuid.uuid4())
            
            with h5py.File(self.db_path, 'a') as f:
                if file_id not in f['files']:
                    logger.error(f"File ID {file_id} not found in database")
                    return None
                
                analysis_group = f['files'][file_id]['analysis'].create_group(analysis_id)
                
                # Store analysis results
                if isinstance(analysis_data, dict):
                    analysis_group.create_dataset('results', data=json.dumps(analysis_data))
                elif isinstance(analysis_data, np.ndarray):
                    analysis_group.create_dataset('results', data=analysis_data)
                else:
                    analysis_group.create_dataset('results', data=str(analysis_data))
                
                # Store analysis metadata
                if analysis_metadata is None:
                    analysis_metadata = {}
                analysis_metadata.update({
                    'analysis_id': analysis_id,
                    'created': datetime.now().isoformat()
                })
                analysis_group.create_dataset('metadata', data=json.dumps(analysis_metadata))
            
            logger.info(f"Added analysis result {analysis_id} for file {file_id}")
            return analysis_id
            
        except Exception as e:
            logger.error(f"Error adding analysis result: {e}")
            return None
    
    def update_file_analysis(self, file_id, analysis_results):
        """Update or add photon data analysis results for a specific file."""
        try:
            if not self.db_path:
                logger.error("No database opened")
                return False
                
            with h5py.File(self.db_path, 'a') as f:
                if file_id not in f['files']:
                    logger.error(f"File ID {file_id} not found in database")
                    return False
                
                file_group = f['files'][file_id]
                
                # Remove existing analysis results if they exist
                if 'photon_analysis' in file_group:
                    del file_group['photon_analysis']
                
                # Create new analysis group
                analysis_group = file_group.create_group('photon_analysis')
                
                # Store analysis results
                analysis_group.create_dataset('results', data=json.dumps(analysis_results))
                
                # Store metadata
                metadata = {
                    'analysis_type': 'photon_data_analysis',
                    'created': datetime.now().isoformat(),
                    'total_peaks': analysis_results.get('total_peak_count', 0),
                    'flowrate': analysis_results.get('flowrate', 0),
                    'has_peaks': len(analysis_results.get('start_bins', [])) > 0
                }
                analysis_group.create_dataset('metadata', data=json.dumps(metadata))
                
                # Update file index with analysis flag
                self._update_file_index(file_id, {'has_analysis': True})
            
            logger.info(f"Updated photon analysis for file {file_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating file analysis: {e}")
            return False
    
    def get_file_data(self, file_id):
        """Retrieve all data for a specific file."""
        try:
            if not self.db_path:
                logger.error("No database opened")
                return None
                
            with h5py.File(self.db_path, 'r') as f:
                if file_id not in f['files']:
                    logger.error(f"File ID {file_id} not found")
                    return None
                
                file_group = f['files'][file_id]
                
                # Get metadata
                metadata = None
                if 'file_metadata' in file_group['metadata']:
                    metadata = json.loads(file_group['metadata']['file_metadata'][()])
                
                # Get raw data
                raw_data = {}
                for key in file_group['raw_data'].keys():
                    data = file_group['raw_data'][key][()]
                    if isinstance(data, bytes):
                        try:
                            # Try to decode as JSON first
                            decoded = data.decode('utf-8')
                            if decoded == 'null':
                                raw_data[key] = None
                            else:
                                raw_data[key] = json.loads(decoded)
                        except (UnicodeDecodeError, json.JSONDecodeError):
                            # If it's not JSON, it might be binary image data
                            raw_data[key] = data
                    else:
                        raw_data[key] = data
                
                # Get analysis results (legacy format)
                analysis_results = {}
                for analysis_id in file_group['analysis'].keys():
                    analysis_group = file_group['analysis'][analysis_id]
                    analysis_results[analysis_id] = {
                        'results': analysis_group['results'][()],
                        'metadata': json.loads(analysis_group['metadata'][()])
                    }
                
                # Get photon analysis results (new format)
                photon_analysis = None
                if 'photon_analysis' in file_group:
                    photon_group = file_group['photon_analysis']
                    photon_analysis = {}
                    
                    if 'results' in photon_group:
                        results_data = photon_group['results'][()]
                        if isinstance(results_data, bytes):
                            results_data = results_data.decode('utf-8')
                        photon_analysis['results'] = results_data
                    
                    if 'metadata' in photon_group:
                        metadata_data = photon_group['metadata'][()]
                        if isinstance(metadata_data, bytes):
                            metadata_data = metadata_data.decode('utf-8')
                        photon_analysis['metadata'] = json.loads(metadata_data)
                
                return {
                    'file_id': file_id,
                    'metadata': metadata,
                    'raw_data': raw_data,
                    'analysis_results': analysis_results,
                    'photon_analysis': photon_analysis
                }
                
        except Exception as e:
            logger.error(f"Error getting file data: {e}")
            return None
    
    def list_files(self):
        """List all files in the database and return as DataFrame with analysis results."""
        columns = ["File ID", "File Name", "File Type", "Peak Count", "Signal CV", "Avg Background", "Avg Fluorescence", "Transit Time", "Eff. Rec. Time"]
        try:
            if not self.db_path:
                logger.error("No database opened")
                return pd.DataFrame(columns=columns)
                
            with h5py.File(self.db_path, 'r') as f:
                file_index = json.loads(f['metadata']['file_index'][()])
                
                if not file_index:
                    # Return empty DataFrame with proper columns
                    return pd.DataFrame(columns=columns)
                
                # Convert file_index dictionary to DataFrame
                records = []
                for file_id, file_info in file_index.items():
                    # Debug: print file_info structure for problematic entries
                    if not file_info.get('original_path') or file_info.get('original_path') == 'Unknown':
                        logger.debug(f"File {file_id} has problematic file_info: {file_info}")
                    
                    # Extract filename from original_path with fallbacks
                    original_path = file_info.get('original_path', 'Unknown')
                    
                    # Try multiple fallback sources for filename
                    if original_path == 'Unknown' or not original_path:
                        # Try to get filename from file_name field
                        file_name = file_info.get('file_name', 'Unknown')
                        if file_name == 'Unknown':
                            # Try other possible field names
                            file_name = file_info.get('name', f"File_{file_id}")
                            if file_name == f"File_{file_id}":
                                # Try to extract from any path-like field
                                for field in file_info.values():
                                    if isinstance(field, str) and ('/' in field or '\\' in field):
                                        potential_name = os.path.basename(field)
                                        if potential_name and potential_name != field:
                                            file_name = potential_name
                                            original_path = field
                                            break
                    else:
                        file_name = os.path.basename(original_path)
                    
                    # Initialize analysis columns with default values
                    peak_count = "N/A"
                    signal_cv = "N/A"
                    avg_background = "N/A"
                    avg_fluorescence = "N/A"
                    transit_time = "N/A"
                    eff_rec_time = "N/A"
                    
                    # Try to get analysis results for this file
                    try:
                        if f'files/{file_id}/photon_analysis' in f:
                            analysis_group = f[f'files/{file_id}/photon_analysis']
                            if 'results' in analysis_group:
                                results_data = analysis_group['results'][()]
                                if isinstance(results_data, bytes):
                                    results_data = results_data.decode('utf-8')
                                
                                analysis_results = json.loads(results_data)
                                peak_count = analysis_results.get('total_peak_count', 0)
                                signal_cv = f"{analysis_results.get('signal_cv', 0):.2f}"
                                avg_background = f"{analysis_results.get('avg_background', 0):.1f}"
                                avg_fluorescence = f"{analysis_results.get('avg_fl_signal', 0):.1f}"
                                transit_time = f"{analysis_results.get('avg_particle_transit_time', 0):.2f}"
                                eff_rec_time = f"{analysis_results.get('effective_recording_time', 0):.2f}"
                    except Exception as e:
                        logger.debug(f"No analysis results for file {file_id}: {e}")
                    
                    # Handle file type with fallbacks
                    file_type = file_info.get('file_type', 'Unknown')
                    if file_type == 'Unknown' and original_path != 'Unknown':
                        # Try to infer from extension
                        ext = os.path.splitext(original_path)[1].lower()
                        if ext in ['.flz', '.fld']:
                            file_type = 'flz'
                        elif ext in ['.flr']:
                            file_type = 'flr'
                        elif ext in ['.flb']:
                            file_type = 'flb'
                    
                    record = {
                        "File ID": file_id,
                        "File Name": file_name,
                        "File Type": file_type,
                        # "File Path": original_path,
                        "Peak Count": peak_count,
                        "Signal CV": signal_cv,
                        "Avg Background": avg_background,
                        "Avg Fluorescence": avg_fluorescence,
                        "Transit Time": transit_time,
                        "Eff. Rec. Time": eff_rec_time
                    }
                    records.append(record)
                
                df = pd.DataFrame(records)
                
                # Check if we have any entries with missing metadata and attempt repair
                unknown_count = len(df[df['File Name'] == 'Unknown'])
                if unknown_count > 0:
                    logger.warning(f"Found {unknown_count} entries with missing metadata, attempting repair...")
                    self._attempt_metadata_repair()
                    # Re-read the data after repair
                    return self.list_files()
                
                logger.debug(f"Retrieved {len(df)} files from database with analysis data")
                return df
                
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            # return pd.DataFrame(columns=["File ID", "File Name", "File Type", "File Path", "Peak Count", "Avg Background", "Transit Time"])
            return pd.DataFrame(columns=columns)
    
    def _attempt_metadata_repair(self):
        """Attempt to repair missing metadata in database entries."""
        try:
            if not self.db_path:
                return False
            
            with h5py.File(self.db_path, 'r+') as f:
                file_index = json.loads(f['metadata']['file_index'][()])
                repaired_count = 0
                
                for file_id, file_info in file_index.items():
                    if not file_info.get('original_path') or file_info.get('original_path') == 'Unknown':
                        logger.debug(f"Attempting to repair metadata for file {file_id}")
                        
                        # Try to find metadata in the HDF5 group
                        if f'files/{file_id}' in f:
                            file_group = f[f'files/{file_id}']
                            
                            # Check attributes for original filename
                            for attr_name in file_group.attrs.keys():
                                attr_value = file_group.attrs[attr_name]
                                if isinstance(attr_value, bytes):
                                    attr_value = attr_value.decode('utf-8', errors='ignore')
                                
                                if isinstance(attr_value, str) and ('/' in attr_value or '\\' in attr_value) and '.' in attr_value:
                                    logger.info(f"Recovered path for {file_id}: {attr_value}")
                                    file_info['original_path'] = attr_value
                                    file_info['file_name'] = os.path.basename(attr_value)
                                    
                                    # Infer file type from extension
                                    ext = os.path.splitext(attr_value)[1].lower()
                                    if ext in ['.flz', '.fld']:
                                        file_info['file_type'] = 'flz'
                                    elif ext == '.flr':
                                        file_info['file_type'] = 'flr'
                                    elif ext == '.flb':
                                        file_info['file_type'] = 'flb'
                                    
                                    repaired_count += 1
                                    break
                            
                            # If no path found, create default based on available data
                            if not file_info.get('original_path') or file_info.get('original_path') == 'Unknown':
                                if 'raw_data' in file_group and 'photon_data' in file_group['raw_data']:
                                    file_info['original_path'] = f"recovered_photon_data_{file_id}.flz"
                                    file_info['file_type'] = 'flz'
                                else:
                                    file_info['original_path'] = f"recovered_file_{file_id}"
                                    file_info['file_type'] = 'unknown'
                                
                                file_info['file_name'] = os.path.basename(file_info['original_path'])
                                file_info['status'] = 'recovered'
                                repaired_count += 1
                
                # Save repaired index
                if repaired_count > 0:
                    f['metadata']['file_index'][()] = json.dumps(file_index).encode('utf-8')
                    logger.info(f"Repaired metadata for {repaired_count} database entries")
                
                return repaired_count > 0
                
        except Exception as e:
            logger.error(f"Error during metadata repair: {e}")
            return False
    
    def delete_file(self, file_id):
        """Delete a file from the database."""
        logger.debug(f"Attempting to delete file: {file_id}")
        try:
            if not self.db_path:
                logger.error("Cannot delete file: No database is currently opened")
                return False
                
            with h5py.File(self.db_path, 'a') as f:
                if file_id not in f['files']:
                    logger.warning(f"File ID '{file_id}' not found in database")
                    return False
                
                logger.debug(f"Removing file group for ID: {file_id}")
                # Delete the file group
                del f['files'][file_id]
                
                # Update file index
                file_index = json.loads(f['metadata']['file_index'][()])
                if file_id in file_index:
                    del file_index[file_id]
                    del f['metadata']['file_index']
                    f['metadata'].create_dataset('file_index', data=json.dumps(file_index))
                    logger.debug("Updated file index after deletion")
            
            logger.info(f"Successfully deleted file '{file_id}' from database")
            return True
            
        except KeyError as e:
            logger.error(f"Key error while deleting file '{file_id}': {e}")
            return False
        except Exception as e:
            logger.critical(f"Critical error deleting file '{file_id}': {e}")
            return False

    def duplicate_file(self, file_id):
        """Duplicate a file in the database."""
        logger.debug(f"Attempting to duplicate file: {file_id}")
        try:
            if not self.db_path:
                logger.error("Cannot duplicate file: No database is currently opened")
                return None
                
            with h5py.File(self.db_path, 'a') as f:
                if file_id not in f['files']:
                    logger.warning(f"File ID '{file_id}' not found in database")
                    return None
                
                # Generate new unique ID for the duplicate
                new_file_id = str(uuid.uuid4())
                logger.debug(f"Generated new ID for duplicate: {new_file_id}")
                
                # Copy the entire file structure
                f.copy(f'files/{file_id}', f['files'], name=new_file_id)
                
                # Update file index with duplicate information
                file_index = json.loads(f['metadata']['file_index'][()])
                if file_id in file_index:
                    duplicate_info = file_index[file_id].copy()
                    
                    # Modify the duplicate's metadata
                    original_name = duplicate_info.get('file_name', duplicate_info.get('original_path', ''))
                    if original_name:
                        # Extract filename and add _copy suffix
                        import os
                        name, ext = os.path.splitext(os.path.basename(original_name))
                        duplicate_info['file_name'] = f"{name}_copy{ext}"
                        if 'original_path' in duplicate_info:
                            path_dir = os.path.dirname(duplicate_info['original_path'])
                            duplicate_info['original_path'] = os.path.join(path_dir, f"{name}_copy{ext}")
                    
                    duplicate_info['duplicated_from'] = file_id
                    duplicate_info['duplicated_at'] = datetime.now().isoformat()
                    duplicate_info['added'] = datetime.now().isoformat()
                    
                    file_index[new_file_id] = duplicate_info
                    
                    # Update the dataset
                    del f['metadata']['file_index']
                    f['metadata'].create_dataset('file_index', data=json.dumps(file_index))
                    logger.debug("Updated file index after duplication")
            
            logger.info(f"Successfully duplicated file '{file_id}' -> '{new_file_id}'")
            return new_file_id
            
        except Exception as e:
            logger.error(f"Error duplicating file '{file_id}': {e}")
            return None

    def rename_file(self, file_id, new_name):
        """Rename a file in the database (updates file_name in metadata)."""
        logger.debug(f"Attempting to rename file: {file_id} -> {new_name}")
        try:
            if not self.db_path:
                logger.error("Cannot rename file: No database is currently opened")
                return False
                
            if not new_name or not new_name.strip():
                logger.error("New file name cannot be empty")
                return False
                
            with h5py.File(self.db_path, 'a') as f:
                if file_id not in f['files']:
                    logger.warning(f"File ID '{file_id}' not found in database")
                    return False
                
                # Update file index with new name
                file_index = json.loads(f['metadata']['file_index'][()])
                if file_id in file_index:
                    file_index[file_id]['file_name'] = new_name.strip()
                    file_index[file_id]['renamed_at'] = datetime.now().isoformat()
                    
                    # Update the dataset
                    del f['metadata']['file_index']
                    f['metadata'].create_dataset('file_index', data=json.dumps(file_index))
                    logger.debug("Updated file index after rename")
                
                # Also update metadata in the file group if it exists
                if 'metadata' in f[f'files/{file_id}'] and 'file_metadata' in f[f'files/{file_id}/metadata']:
                    try:
                        metadata_str = f[f'files/{file_id}/metadata/file_metadata'][()]
                        if isinstance(metadata_str, bytes):
                            metadata_str = metadata_str.decode('utf-8')
                        
                        metadata = json.loads(metadata_str)
                        metadata['file_name'] = new_name.strip()
                        metadata['renamed_at'] = datetime.now().isoformat()
                        
                        # Update the metadata dataset
                        del f[f'files/{file_id}/metadata/file_metadata']
                        f[f'files/{file_id}/metadata'].create_dataset('file_metadata', data=json.dumps(metadata))
                        logger.debug("Updated file metadata after rename")
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.debug(f"Could not update file metadata: {e}")
            
            logger.info(f"Successfully renamed file '{file_id}' to '{new_name}'")
            return True
            
        except Exception as e:
            logger.error(f"Error renaming file '{file_id}': {e}")
            return False
    
    def merge_databases(self, other_db_path):
        """Merge another FLDB database into the current one."""
        try:
            if not self.db_path:
                logger.error("No database opened")
                return False
                
            with h5py.File(other_db_path, 'r') as other_db, h5py.File(self.db_path, 'a') as current_db:
                # Copy all files from other database
                for file_id in other_db['files'].keys():
                    # Generate new unique ID to avoid conflicts
                    new_id = str(uuid.uuid4())
                    
                    # Copy the entire file structure
                    other_db.copy(f'files/{file_id}', current_db['files'], name=new_id)
                    
                    # Update file index
                    other_index = json.loads(other_db['metadata']['file_index'][()])
                    if file_id in other_index:
                        file_info = other_index[file_id]
                        file_info['merged_from'] = other_db_path
                        file_info['merged_at'] = datetime.now().isoformat()
                        self._update_file_index(new_id, file_info)
            
            logger.info(f"Successfully merged database: {other_db_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error merging databases: {e}")
            return False
    
    def save_database(self, new_path=None):
        """Save/copy the database to a new location."""
        try:
            if not self.db_path:
                logger.error("No database opened")
                return False
                
            if new_path is None:
                logger.info("Database is automatically saved")
                return True
            
            # Copy current database to new location
            import shutil
            shutil.copy2(self.db_path, new_path)
            logger.info(f"Database saved to: {new_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving database: {e}")
            return False
    
    def _extract_flz_contents(self, zip_file):
        """Extract contents from FLZ zip file."""
        file_data = {
            'metadata': None,
            'alignment_image': None,
            'laser_on_image': None,
            'photon_data': None
        }
        
        file_list = zip_file.namelist()
        
        # Extract metadata.json
        if 'metadata.json' in file_list:
            with zip_file.open('metadata.json') as f:
                file_data['metadata'] = json.loads(f.read().decode('utf-8'))
        
        # Extract images
        if 'Alignment_Image.png' in file_list:
            with zip_file.open('Alignment_Image.png') as f:
                img = Image.open(io.BytesIO(f.read()))
                file_data['alignment_image'] = np.array(img)
        
        if 'LaserOn_Image.png' in file_list:
            with zip_file.open('LaserOn_Image.png') as f:
                img = Image.open(io.BytesIO(f.read()))
                file_data['laser_on_image'] = np.array(img)
        
        # Extract photon data
        if 'photon_data.flr' in file_list:
            with zip_file.open('photon_data.flr') as f:
                file_data['photon_data'] = np.frombuffer(f.read(), dtype=np.uint8)
        
        return file_data
    
    def _update_file_index(self, file_id, file_info):
        """Update the file index with new file information."""
        with h5py.File(self.db_path, 'a') as f:
            current_index = json.loads(f['metadata']['file_index'][()])
            
            # If file_id exists, merge with existing info instead of replacing
            if file_id in current_index:
                current_index[file_id].update(file_info)
            else:
                current_index[file_id] = file_info
            
            # Update the dataset
            del f['metadata']['file_index']
            f['metadata'].create_dataset('file_index', data=json.dumps(current_index))
    
    def get_database_info(self):
        """Get database information and statistics."""
        logger.debug("Retrieving database information and statistics")
        try:
            if not self.db_path:
                logger.error("Cannot get database info: No database is currently opened")
                return None
                
            if not os.path.exists(self.db_path):
                logger.error(f"Database file not found: {self.db_path}")
                return None
                
            with h5py.File(self.db_path, 'r') as f:
                logger.debug("Reading database metadata")
                db_info = json.loads(f['metadata']['db_info'][()])
                file_index = json.loads(f['metadata']['file_index'][()])
                
                # Calculate statistics
                total_files = len(file_index)
                file_types = {}
                for file_info in file_index.values():
                    file_type = file_info.get('file_type', 'unknown')
                    file_types[file_type] = file_types.get(file_type, 0) + 1
                
                logger.debug(f"Database statistics: {total_files} files, types: {file_types}")
                
                file_size_bytes = os.path.getsize(self.db_path)
                file_size_mb = int(file_size_bytes / (1024 * 1024))
                
                result = {
                    'database info': db_info,
                    'total files': total_files,
                    'file types': file_types,
                    'database path': self.db_path,
                    'file size (MB)': file_size_mb
                }
                
                logger.debug("Successfully retrieved database information")
                return result
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in database metadata: {e}")
            return None
        except KeyError as e:
            logger.error(f"Missing required metadata in database: {e}")
            return None
        except OSError as e:
            logger.error(f"File system error accessing database: {e}")
            return None
        except Exception as e:
            logger.critical(f"Critical error getting database info: {e}")
            return None

    # Legacy methods for backward compatibility
    def load_csv(self, file_path):
        """Legacy method to load CSV files."""
        try:
            self.legacy_data = pd.read_csv(file_path)
            logger.info(f"Loaded CSV file: {file_path}")
        except Exception as e:
            logger.error(f"Error loading CSV file {file_path}: {e}")
            self.legacy_data = pd.DataFrame()

    def get_data(self):
        """Legacy method to get loaded CSV data."""
        if hasattr(self, 'legacy_data'):
            return self.legacy_data
        return pd.DataFrame()

    def save_csv(self, file_path):
        """Legacy method to save CSV files."""
        try:
            if hasattr(self, 'legacy_data'):
                self.legacy_data.to_csv(file_path, index=False)
                logger.info(f"Saved CSV file: {file_path}")
            else:
                logger.warning("No data to save")
        except Exception as e:
            logger.error(f"Error saving CSV file {file_path}: {e}")
