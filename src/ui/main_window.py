import dearpygui.dearpygui as dpg
import contextlib
from .file_dialogs import FileDialogs
from .tables import TableViewer
from .graphs import GraphViewer
from .widgets import StatusBar, ProgressBar

@contextlib.contextmanager
def align_items(n_cols_left: int, n_cols_right: int) -> int | str:
	"""
	Adds a table to align items.

	Please note:
	Many items (e.g. combo, drag_*, input_*, slider_*, listbox, progress_bar) will not display unless a positive width is set

	Args:
		n_cols_left: Align n items to the left. (n_cols_left)
		n_cols_right: Align n items to the right (n_cols_right)
	"""
	if n_cols_left < 0 or n_cols_right < 0:
		raise ValueError("Column amount must be 0 or higher")

	table = dpg.add_table(resizable=False, header_row=False, policy=0)
	for _ in range(n_cols_left - 1):
		dpg.add_table_column(width_stretch=False, width_fixed=True, parent=table)
	dpg.add_table_column(width_stretch=False, width_fixed=False, parent=table)
	for _ in range(n_cols_right):
		dpg.add_table_column(width_stretch=False, width_fixed=True, parent=table)
	widget = dpg.add_table_row(parent=table)
	if n_cols_left == 0:
		dpg.add_spacer(parent=widget)

	dpg.push_container_stack(widget)
	try:
		yield widget
	finally:
		dpg.pop_container_stack()

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
            self.table_viewer.create("primary_window")
        
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
            dpg.add_text("Row Details", tag="details_title")
            dpg.add_text("Select a row to see details.", tag="details_placeholder")
        
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
            # Use align_items to properly align menu items to the left and status/progress to the right
            with align_items(1, 2):
                # Left-aligned menu items (column 0)
                with dpg.group(horizontal=True):
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
                
                
                # Progress bar in menu bar (ensure it has proper width)
                self.progress_bar.create("menu_bar")
                
                # Status bar in menu bar (ensure it has proper width)
                self.status_bar.create("menu_bar")

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
