import dearpygui.dearpygui as dpg
from .file_dialogs import FileDialogs
from .tables import TableViewer
from .graphs import GraphViewer
from .widgets import StatusBar, ProgressBar

class MainWindow:
    def __init__(self, app):
        self.app = app
        self.file_dialogs = FileDialogs(app)
        self.table_viewer = TableViewer()
        self.graph_viewer = GraphViewer()
        self.status_bar = StatusBar()
        self.progress_bar = ProgressBar()

    def create(self):
        """Creates the main application window with fixed menu and status bars."""
        # Create primary window first
        with dpg.window(tag="primary_window", show=True, no_title_bar=True):
            
            # Menu bar
            self._create_menu_bar()
            
            # Main content
            dpg.add_text("MAIN TABLE AREA", color=(0, 255, 0))
            self.table_viewer.create("primary_window")
            
            # Status bar
            dpg.add_separator()
            dpg.add_text("STATUS BAR", color=(255, 100, 100))
            self.status_bar.create("primary_window")
        
        # Create dockable windows
        self._create_simple_dockable_windows()
        
        # Configure docking with layout persistence AFTER windows are created
        import os
        try:
            # Use absolute path to config folder
            config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config")
            layout_file = os.path.join(config_dir, "layout.ini")
            # Ensure config directory exists
            os.makedirs(config_dir, exist_ok=True)
            dpg.configure_app(docking=True, docking_space=True, init_file=layout_file)
            
            # Load font scale from settings
            self._load_font_scale()
        except Exception as excpt:
            print(excpt)

        self.setup_drag_and_drop()
    
    def _load_font_scale(self):
        """Load saved font scale from config file."""
        try:
            import json
            import os
            config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config")
            settings_file = os.path.join(config_dir, "settings.json")
            
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
                    font_scale = settings.get('font_scale', 0.5)
                    dpg.set_global_font_scale(font_scale)
                    print(f"Font scale loaded: {font_scale}")
        except Exception as e:
            print(f"Failed to load font scale: {e}")
            # Default font scale if loading fails
            dpg.set_global_font_scale(0.5)
    
    def _save_font_scale(self):
        """Save current font scale to config file."""
        try:
            import json
            import os
            config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config")
            settings_file = os.path.join(config_dir, "settings.json")
            
            # Ensure config directory exists
            os.makedirs(config_dir, exist_ok=True)
            
            # Load existing settings or create new
            settings = {}
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
            
            # Update font scale
            settings['font_scale'] = dpg.get_global_font_scale()
            
            # Save settings
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
            
            print(f"Font scale saved: {settings['font_scale']}")
        except Exception as e:
            print(f"Failed to save font scale: {e}")
    
    def _decrease_font_size(self):
        """Decrease font size and save setting."""
        current_scale = dpg.get_global_font_scale()
        new_scale = max(0.1, current_scale - 0.1)  # Minimum scale of 0.1
        dpg.set_global_font_scale(new_scale)
        self._save_font_scale()
    
    def _increase_font_size(self):
        """Increase font size and save setting."""
        current_scale = dpg.get_global_font_scale()
        new_scale = min(3.0, current_scale + 0.1)  # Maximum scale of 3.0
        dpg.set_global_font_scale(new_scale)
        self._save_font_scale()

    def _create_simple_dockable_windows(self):
        """Create simple dockable windows to test docking."""
        
        # Functions Window - dockable
        with dpg.window(label="Functions", tag="functions_window", width=250, height=300, pos=[800, 100]):
            dpg.add_text("Function Panel")
            dpg.add_button(label="Load CSV", callback=self._load_csv)
            dpg.add_button(label="Analyze Data")
        
        # Details Window - dockable
        with dpg.window(label="Details", tag="details_window", width=300, height=200, pos=[800, 450]):
            dpg.add_text("Row Details")
            dpg.add_text("Select a row to see details.")
        
        # Graph Window - dockable
        with dpg.window(label="Graph", tag="graph_window", width=400, height=300, pos=[50, 400], show=False):
            dpg.add_text("Graph will appear here")
            self.graph_viewer.create("graph_window")

    def _load_csv(self):
        """Open file dialog to load CSV."""
        dpg.show_item("file_drop_dialog")

    def _exit_application(self):
        """Exit application."""
        self._save_font_scale()
        dpg.stop_dearpygui()

    def _create_menu_bar(self):
        with dpg.menu_bar():
            with dpg.menu(label="File"):
                with dpg.menu(label="Project"):
                    dpg.add_menu_item(label="New", callback=lambda: print("New project"))
                    dpg.add_menu_item(label="Load", callback=lambda: print("Load project"))
                    dpg.add_menu_item(label="Save", callback=lambda: print("Save project"))
                    dpg.add_menu_item(label="Save as..", callback=lambda: print("Save project as"))
                    dpg.add_menu_item(label="Close", callback=lambda: print("Close project"))
                dpg.add_separator()
                with dpg.menu(label="FLR"):
                    dpg.add_menu_item(label="Add", callback=lambda: print("Add FLR"))
                    dpg.add_menu_item(label="Open from folder", callback=lambda: print("Open FLR from folder"))
                with dpg.menu(label="FLB"):
                    dpg.add_menu_item(label="Add", callback=lambda: print("Add FLB"))
                    dpg.add_menu_item(label="Open from folder", callback=lambda: print("Open FLB from folder"))
                dpg.add_separator()
                dpg.add_menu_item(label="Exit", callback=self._exit_application)

            with dpg.menu(label="View"):
                dpg.add_menu_item(label="Show Graph", callback=lambda: dpg.show_item("graph_window"))
                dpg.add_menu_item(label="Show Functions", callback=lambda: dpg.show_item("functions_window"))
                dpg.add_menu_item(label="Show Details", callback=lambda: dpg.show_item("details_window"))
                dpg.add_separator()
                dpg.add_menu_item(label="Decrease Font Size", callback=self._decrease_font_size)
                dpg.add_menu_item(label="Increase Font Size", callback=self._increase_font_size)
                dpg.add_separator()
                # dpg.add_menu_item(label="Layout Info", callback=lambda: print("Layout is automatically saved to config/layout.ini"))

            with dpg.menu(label="Plugins"):
                # This could be populated by the plugin manager
                pass

    def setup_drag_and_drop(self):
        """Sets up the drag and drop payload for file opening."""
        with dpg.handler_registry():
            dpg.add_mouse_drag_handler(callback=self._on_drag)

        with dpg.file_dialog(directory_selector=False, show=False, callback=self._on_file_drop, tag="file_drop_dialog", width=500, height=400):
            dpg.add_file_extension(".*")
            dpg.add_file_extension(".csv")

    def _on_drag(self, sender, app_data):
        # This is a simplified drag-and-drop handler.
        # A more robust implementation is needed for real applications.
        if dpg.is_mouse_button_released(dpg.mvMouseButton_Left):
            # This is a placeholder for where you'd handle the drop
            # In a real app, you'd check if a file is being dropped onto the viewport
            pass

    def _on_file_drop(self, sender, app_data):
        if 'file_path_name' in app_data:
            self.app.open_file(app_data['file_path_name'])
        dpg.hide_item("file_drop_dialog")
