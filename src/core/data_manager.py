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
            with h5py.File(self.db_path, 'a', compression='gzip', compression_opts=6) as f:
                file_group = f['files'].create_group(unique_id)
                
                # Store metadata
                metadata_group = file_group.create_group('metadata')
                if file_data['metadata']:
                    metadata_group.create_dataset('file_metadata', data=json.dumps(file_data['metadata']))
                
                # Store raw data
                raw_group = file_group.create_group('raw_data')
                
                # Store images
                if file_data['alignment_image'] is not None:
                    raw_group.create_dataset('alignment_image', data=file_data['alignment_image'])
                else:
                    raw_group.create_dataset('alignment_image', data=json.dumps(None))
                    
                if file_data['laser_on_image'] is not None:
                    raw_group.create_dataset('laser_on_image', data=file_data['laser_on_image'])
                else:
                    raw_group.create_dataset('laser_on_image', data=json.dumps(None))
                
                # Store photon data
                if file_data['photon_data'] is not None:
                    raw_group.create_dataset('photon_data', data=file_data['photon_data'])
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
            with h5py.File(self.db_path, 'a', compression='gzip', compression_opts=6) as f:
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
            with h5py.File(self.db_path, 'a', compression='gzip', compression_opts=6) as f:
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
            
            with h5py.File(self.db_path, 'a', compression='gzip', compression_opts=6) as f:
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
                    if isinstance(data, bytes) and data.startswith(b'null'):
                        raw_data[key] = None
                    else:
                        raw_data[key] = data
                
                # Get analysis results
                analysis_results = {}
                for analysis_id in file_group['analysis'].keys():
                    analysis_group = file_group['analysis'][analysis_id]
                    analysis_results[analysis_id] = {
                        'results': analysis_group['results'][()],
                        'metadata': json.loads(analysis_group['metadata'][()])
                    }
                
                return {
                    'file_id': file_id,
                    'metadata': metadata,
                    'raw_data': raw_data,
                    'analysis_results': analysis_results
                }
                
        except Exception as e:
            logger.error(f"Error getting file data: {e}")
            return None
    
    def list_files(self):
        """List all files in the database."""
        try:
            if not self.db_path:
                logger.error("No database opened")
                return []
                
            with h5py.File(self.db_path, 'r') as f:
                file_index = json.loads(f['metadata']['file_index'][()])
                return file_index
                
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return []
    
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
                file_size_mb = file_size_bytes / (1024 * 1024)
                
                result = {
                    'database_info': db_info,
                    'total_files': total_files,
                    'file_types': file_types,
                    'database_path': self.db_path,
                    'file_size_mb': file_size_mb,
                    'file_size_bytes': file_size_bytes
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
