import dearpygui.dearpygui as dpg
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

    def run(self):
        """Run the application's main loop."""
        # This is handled by DearPyGui's start_dearpygui in main.py
        pass

    def open_file(self, file_path):
        """Callback to open a file."""
        self.data_manager.load_csv(file_path)
        # Update UI, e.g., table
        self.main_window.table_viewer.update_data(self.data_manager.get_data())

    def save_file(self, file_path):
        """Callback to save a file."""
        self.data_manager.save_csv(file_path)
