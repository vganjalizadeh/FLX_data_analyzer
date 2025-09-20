#!/usr/bin/env python3
"""
Database Repair Utility for FLX Data Analyzer

This utility helps repair database entries that have missing or corrupted file metadata.
Run this if you see "Unknown" file names in the table after analysis.
"""

import h5py
import json
import os
from src.core.data_manager import DataManager

def repair_database_metadata(db_path):
    """Repair missing metadata in database file entries."""
    print(f"Repairing database: {db_path}")
    
    with h5py.File(db_path, 'r+') as f:
        # Load current file index
        file_index = json.loads(f['metadata']['file_index'][()])
        
        repaired_count = 0
        
        for file_id, file_info in file_index.items():
            # Check if this entry needs repair
            needs_repair = False
            
            if not file_info.get('original_path') or file_info.get('original_path') == 'Unknown':
                print(f"File {file_id} needs metadata repair")
                needs_repair = True
                
                # Try to reconstruct metadata from HDF5 group structure
                if f'files/{file_id}' in f:
                    file_group = f[f'files/{file_id}']
                    
                    # Check if there are any attributes that might have the original filename
                    for attr_name in file_group.attrs.keys():
                        attr_value = file_group.attrs[attr_name]
                        if isinstance(attr_value, (str, bytes)):
                            if isinstance(attr_value, bytes):
                                attr_value = attr_value.decode('utf-8', errors='ignore')
                            
                            # Check if this looks like a file path
                            if ('/' in attr_value or '\\' in attr_value) and ('.' in attr_value):
                                print(f"  Found potential path in attribute {attr_name}: {attr_value}")
                                file_info['original_path'] = attr_value
                                file_info['file_name'] = os.path.basename(attr_value)
                                
                                # Try to infer file type from extension
                                ext = os.path.splitext(attr_value)[1].lower()
                                if ext in ['.flz', '.fld']:
                                    file_info['file_type'] = 'flz'
                                elif ext == '.flr':
                                    file_info['file_type'] = 'flr'
                                elif ext == '.flb':
                                    file_info['file_type'] = 'flb'
                                
                                needs_repair = False
                                repaired_count += 1
                                break
                    
                    # If still no path found, create a reasonable default
                    if needs_repair:
                        # Check what data types are available to guess file type
                        if 'raw_data' in file_group:
                            raw_group = file_group['raw_data']
                            if 'photon_data' in raw_group:
                                file_info['file_type'] = 'flz'
                                file_info['original_path'] = f"recovered_file_{file_id}.flz"
                            else:
                                file_info['file_type'] = 'unknown'
                                file_info['original_path'] = f"recovered_file_{file_id}"
                        
                        file_info['file_name'] = os.path.basename(file_info['original_path'])
                        file_info['status'] = 'recovered'
                        repaired_count += 1
                        print(f"  Created default metadata for {file_id}")
            
        # Save repaired file index
        if repaired_count > 0:
            f['metadata']['file_index'][()] = json.dumps(file_index).encode('utf-8')
            print(f"Repaired {repaired_count} database entries")
        else:
            print("No entries needed repair")
    
    print("Database repair complete")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python database_repair_utility.py <database_path>")
        sys.exit(1)
    
    db_path = sys.argv[1]
    if not os.path.exists(db_path):
        print(f"Database file not found: {db_path}")
        sys.exit(1)
    
    repair_database_metadata(db_path)