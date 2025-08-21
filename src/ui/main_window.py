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
        # Create primary window WITHOUT docking first to ensure menu/status bars work
        with dpg.window(tag="primary_window"):
            
            # Menu bar
            self._create_menu_bar()
            
            # Main content
            dpg.add_text("MAIN TABLE AREA", color=(0, 255, 0))
            self.table_viewer.create("primary_window")
            
            # Status bar
            dpg.add_separator()
            dpg.add_text("STATUS BAR", color=(255, 100, 100))
            self.status_bar.create("primary_window")
        
        # Enable docking AFTER primary window is created
        dpg.configure_app(docking=True, docking_space=True)
        
        # Create dockable windows
        self._create_simple_dockable_windows()
        
        self.setup_drag_and_drop()

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

    def _load_layout(self):
        """Load saved docking layout or set default positions."""
        try:
            # Try to load from config file
            import json
            import os
            config_path = "config/layout.json"
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    layout = json.load(f)
                    for window_id, props in layout.items():
                        if dpg.does_item_exist(window_id):
                            dpg.set_item_pos(window_id, props.get('pos', [100, 100]))
                            dpg.set_item_width(window_id, props.get('width', 300))
                            dpg.set_item_height(window_id, props.get('height', 200))
                            if props.get('show', True):
                                dpg.show_item(window_id)
                return
        except:
            pass
        
        # Set default layout if no config found
        self._set_default_layout()

    def _set_default_layout(self):
        """Set the default docking arrangement."""
        # Position dockable windows around the main table
        dpg.set_item_pos("functions_window", [50, 100])
        dpg.set_item_pos("details_window", [50, 520])
        dpg.set_item_pos("graph_window", [400, 100])
        
        # Show default windows
        dpg.show_item("functions_window")
        dpg.show_item("details_window")

    def _save_layout(self):
        """Save current docking layout to config file."""
        try:
            import json
            import os
            
            # Ensure config directory exists
            os.makedirs("config", exist_ok=True)
            
            layout = {}
            for window_id in ["graph_window", "functions_window", "details_window"]:
                if dpg.does_item_exist(window_id):
                    layout[window_id] = {
                        'pos': dpg.get_item_pos(window_id),
                        'width': dpg.get_item_width(window_id),
                        'height': dpg.get_item_height(window_id),
                        'show': dpg.is_item_shown(window_id)
                    }
            
            with open("config/layout.json", 'w') as f:
                json.dump(layout, f, indent=2)
            
            print("Layout saved successfully")
        except Exception as e:
            print(f"Failed to save layout: {e}")

    def _reset_docking_layout(self):
        """Reset all dockable windows to their default positions."""
        self._set_default_layout()
        print("Layout reset to default positions")

    def _exit_application(self):
        """Save layout and exit application."""
        self._save_layout()
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
                dpg.add_menu_item(label="Reset Layout", callback=self._reset_docking_layout)
                dpg.add_menu_item(label="Save Layout", callback=self._save_layout)

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
