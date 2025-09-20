import dearpygui.dearpygui as dpg
import pandas as pd
import os
from src.ui.main_window import MainWindow
from src.core.data_manager import DataManager
from src.core.plugin_manager import PluginManager

class App:
    def __init__(self):
        self.data_manager = DataManager()
        self.plugin_manager = PluginManager()
        self.main_window = MainWindow(self)

    def setup(self):
        """Initial setup of the application."""
        self.main_window.create()
        self.plugin_manager.load_plugins()
        # self.main_window.setup_drag_and_drop() # Example of how you might set this up
        
        # Auto-load database if it exists
        self._auto_load_database()

    def run(self):
        """Run the application's main loop."""
        # This is handled by DearPyGui's start_dearpygui in main.py
        pass

    def open_file(self, file_path):
        """Callback to open a file."""
        file_ext = file_path.lower().split('.')[-1]
        
        try:
            if file_ext == 'flz':
                file_id = self.data_manager.add_flz_file(file_path)
                print(f"Added FLZ file with ID: {file_id}")
                # Refresh the table with database records
                self.refresh_table_from_database()
            elif file_ext == 'flr':
                file_id = self.data_manager.add_flr_file(file_path)
                print(f"Added FLR file with ID: {file_id}")
                self.refresh_table_from_database()
            elif file_ext == 'flb':
                file_id = self.data_manager.add_flb_file(file_path)
                print(f"Added FLB file with ID: {file_id}")
                self.refresh_table_from_database()
            elif file_ext == 'csv':
                # Legacy CSV support
                self.data_manager.load_csv(file_path)
                self.main_window.table_viewer.update_data(self.data_manager.get_data())
            else:
                print(f"Unsupported file type: {file_ext}")
        except Exception as e:
            print(f"Error opening file {file_path}: {e}")

    def save_file(self, file_path):
        """Callback to save a file."""
        try:
            self.data_manager.save_csv(file_path)
        except Exception as e:
            print(f"Error saving file {file_path}: {e}")

    def refresh_table_from_database(self):
        """Refresh the table with current database records."""
        try:
            files_data = self.data_manager.list_files()
            if files_data is not None and isinstance(files_data, pd.DataFrame):
                self.main_window.table_viewer.load_database_records(files_data)
                print(f"Refreshed table with {len(files_data)} database records")
            else:
                print("No database records found")
        except Exception as e:
            print(f"Error refreshing table from database: {e}")

    def get_file_data(self, file_id):
        """Get detailed file data from database."""
        try:
            return self.data_manager.get_file_data(file_id)
        except Exception as e:
            print(f"Error getting file data for {file_id}: {e}")
            return None
    
    def _auto_load_database(self):
        """Automatically load a default database if it exists."""
        
        # Look for a default database file
        default_db_paths = [
            "data.fldb",
            "database.fldb", 
            "flx_data.fldb",
            os.path.join(os.getcwd(), "data.fldb"),
            os.path.join(os.path.dirname(__file__), "..", "..", "data.fldb")
        ]
        
        for db_path in default_db_paths:
            if os.path.exists(db_path):
                try:
                    print(f"Auto-loading database: {db_path}")
                    self.data_manager.open_database(db_path)
                    self.refresh_table_from_database()
                    if hasattr(self.main_window, 'status_bar'):
                        self.main_window.status_bar.set_status(f"Loaded database: {os.path.basename(db_path)}")
                    break
                except Exception as e:
                    print(f"Failed to auto-load database {db_path}: {e}")
                    continue
        else:
            # No database found, create a new one
            try:
                default_db = "data.fldb"
                print(f"Creating new database: {default_db}")
                self.data_manager.create_database(default_db)
                if hasattr(self.main_window, 'status_bar'):
                    self.main_window.status_bar.set_status(f"Created new database: {default_db}")
            except Exception as e:
                print(f"Failed to create new database: {e}")
    
    def import_database(self, db_path):
        """Import a database file."""
        try:
            self.data_manager.open_database(db_path)
            self.refresh_table_from_database()
            if hasattr(self.main_window, 'status_bar'):
                self.main_window.status_bar.set_status(f"Imported database: {os.path.basename(db_path)}")
            print(f"Successfully imported database: {db_path}")
        except Exception as e:
            print(f"Error importing database {db_path}: {e}")
            if hasattr(self.main_window, 'status_bar'):
                self.main_window.status_bar.set_status(f"Failed to import database: {str(e)}")
    
    def export_database(self, target_path):
        """Export current database to a new location."""
        import shutil
        try:
            if not self.data_manager.db_path:
                raise ValueError("No database currently open")
            
            shutil.copy2(self.data_manager.db_path, target_path)
            if hasattr(self.main_window, 'status_bar'):
                self.main_window.status_bar.set_status(f"Exported database to: {os.path.basename(target_path)}")
            print(f"Successfully exported database to: {target_path}")
        except Exception as e:
            print(f"Error exporting database to {target_path}: {e}")
            if hasattr(self.main_window, 'status_bar'):
                self.main_window.status_bar.set_status(f"Failed to export database: {str(e)}")
    
    def update_file_analysis(self, file_id, analysis_results):
        """Update photon data analysis results for a file."""
        try:
            success = self.data_manager.update_file_analysis(file_id, analysis_results)
            if success and hasattr(self.main_window, 'status_bar'):
                peak_count = analysis_results.get('total_peak_count', 0)
                self.main_window.status_bar.set_status(f"Analysis complete: {peak_count} peaks detected")
            return success
        except Exception as e:
            print(f"Error updating file analysis: {e}")
            if hasattr(self.main_window, 'status_bar'):
                self.main_window.status_bar.set_status(f"Analysis failed: {str(e)}")
            return False
