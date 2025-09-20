import dearpygui.dearpygui as dpg
import contextlib
import pandas as pd
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
        self.table_viewer = TableViewer(app)
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
        new_scale = max(0.1, current_scale - 0.2 * current_scale)  # Minimum scale of 0.1
        dpg.set_global_font_scale(new_scale)
        self._save_font_scale()
    
    def _increase_font_size(self):
        """Increase font size and save setting."""
        current_scale = dpg.get_global_font_scale()
        new_scale = min(3.0, current_scale + 0.2 * current_scale)  # Maximum scale of 3.0
        dpg.set_global_font_scale(new_scale)
        self._save_font_scale()

    def _create_simple_dockable_windows(self):
        """Create simple dockable windows to test docking."""
        
        # Functions Window - dockable
        with dpg.window(label="Functions", tag="functions_window", width=280, height=400, pos=[800, 100]):
            dpg.add_text("Data Manager Functions", color=[100, 200, 255])
            dpg.add_separator()
            
            # FLZ File Operations
            dpg.add_text("FLZ Files:", color=[200, 200, 100])
            dpg.add_button(label="Add FLZ File", callback=self._add_flz_file, width=-1)
            dpg.add_button(label="Add FLZ Folder", callback=self._add_flz_folder, width=-1)
            dpg.add_separator()
            
            # FLR File Operations  
            dpg.add_text("FLR Files:", color=[200, 200, 100])
            dpg.add_button(label="Add FLR File", callback=self._add_flr_file, width=-1)
            dpg.add_button(label="Add FLR Folder", callback=self._add_flr_folder, width=-1)
            dpg.add_separator()
            
            # FLB File Operations
            dpg.add_text("FLB Files:", color=[200, 200, 100])
            dpg.add_button(label="Add FLB File", callback=self._add_flb_file, width=-1)
            dpg.add_button(label="Add FLB Folder", callback=self._add_flb_folder, width=-1)
            dpg.add_separator()
            
            # Database Operations
            dpg.add_text("Database:", color=[200, 200, 100])
            dpg.add_button(label="Import Database", callback=self._import_database, width=-1)
            dpg.add_button(label="Export Database", callback=self._export_database, width=-1)
            dpg.add_button(label="Refresh Table", callback=self._refresh_table, width=-1)
            dpg.add_button(label="Database Info", callback=self._show_database_info, width=-1)
            dpg.add_separator()
            
            # Legacy Operations
            dpg.add_text("Legacy:", color=[150, 150, 150])
            dpg.add_button(label="Load CSV", callback=self._load_csv, width=-1)
        
        # Details Window - dockable (larger for detailed analysis)
        with dpg.window(label="Details", tag="details_window", width=500, height=600, pos=[800, 450]):
            dpg.add_text("Select a row to see details.", tag="details_placeholder")
            
            # Create persistent plot structure for photon data
            self._create_persistent_plot_structure()
        
        # Graph Window - dockable
        with dpg.window(label="Graph", tag="graph_window", width=400, height=300, pos=[50, 400], show=False):
            dpg.add_text("Graph will appear here")
            self.graph_viewer.create("graph_window")

    def _create_persistent_plot_structure(self):
        """Create the persistent plot structure for photon data analysis."""
        dpg.add_spacer(height=10)
        
        # Statistics section (initially hidden)
        with dpg.group(tag="statistics_group", show=False):
            dpg.add_text("Statistics:", color=[150, 200, 150])
            with dpg.group(horizontal=True):
                dpg.add_text("Avg Rate:", color=[200, 200, 200])
                dpg.add_text("0.00 kcps", color=[255, 255, 100], tag="avg_rate_text")
            with dpg.group(horizontal=True):
                dpg.add_text("Std Dev:", color=[200, 200, 200])
                dpg.add_text("0.00 kcps", color=[255, 255, 100], tag="std_rate_text")
            with dpg.group(horizontal=True):
                dpg.add_text("Min Rate:", color=[200, 200, 200])
                dpg.add_text("0.00 Mcps", color=[255, 255, 100], tag="min_rate_text")
            with dpg.group(horizontal=True):
                dpg.add_text("Max Rate:", color=[200, 200, 200])
                dpg.add_text("0.00 Mcps", color=[255, 255, 100], tag="max_rate_text")
            dpg.add_spacer(height=10)
        
        # Controls section (initially hidden)
        with dpg.group(tag="plot_controls_group", show=False):
            dpg.add_text("Plot Controls:", color=[150, 200, 150])
            with dpg.group(horizontal=True):
                # Deadtime correction checkbox
                dpg.add_checkbox(label="Deadtime Correction", default_value=True, 
                               tag="persistent_deadtime_checkbox",
                               callback=lambda: self.table_viewer._update_persistent_plot())
                
                # Deadtime value input
                dpg.add_spacer(width=10)
                dpg.add_text("Deadtime (ns):", color=[200, 200, 200])
                dpg.add_input_float(default_value=22.0, width=150, tag="persistent_deadtime_input",
                                  min_value=0.1, max_value=100.0, format="%.1f", on_enter=True,
                                  callback=lambda: self.table_viewer._update_persistent_plot())
                
                # Rebin value input
                dpg.add_spacer(width=20)
                dpg.add_text("Rebin (us):", color=[200, 200, 200])
                dpg.add_input_int(default_value=5, width=150, tag="persistent_rebin_input", 
                                min_value=1, max_value=1000, on_enter=True,
                                callback=lambda: self.table_viewer._update_persistent_plot())
                
                # Analysis button
                dpg.add_spacer(width=30)
                dpg.add_button(label="Analyze", width=100, height=30, 
                             tag="analyze_photon_button",
                             callback=lambda: self.table_viewer._analyze_current_photon_data())
            
            # Progress bar for analysis (initially hidden)
            with dpg.group(tag="analysis_progress_group", show=False):
                dpg.add_text("Analyzing photon data...", color=[200, 200, 100], tag="analysis_status_text")
                dpg.add_progress_bar(label="Analysis Progress", width=-1, height=4, tag="analysis_progress_bar")
            
            dpg.add_spacer(height=10)
        
        # Persistent plot (initially hidden)
        with dpg.plot(label="Photon Count vs Time", height=300, width=-1, 
                     tag="persistent_photon_plot", show=False):
            dpg.add_plot_legend()
            dpg.add_plot_axis(dpg.mvXAxis, label="Time (s)", tag="persistent_x_axis")
            with dpg.plot_axis(dpg.mvYAxis, label="Photon Count (Mcps)", lock_min=True, tag="persistent_y_axis"):
                dpg.add_line_series([0,1], [15, 15], label="Photon Count", tag="persistent_line_series")
                # Add persistent scatter series for peak markers
                dpg.add_scatter_series([], [], label="Peak Starts", tag="peak_starts_scatter")
                dpg.add_scatter_series([], [], label="Peak Ends", tag="peak_ends_scatter")
        
        dpg.bind_item_theme("persistent_photon_plot", self.table_viewer.plot_themes['photon_plot'])
        # Apply themes to peak marker scatter series
        with dpg.theme(tag="peak_starts_theme"):
            with dpg.theme_component(dpg.mvScatterSeries):
                dpg.add_theme_color(dpg.mvPlotCol_MarkerFill, [150, 255, 0, 255], category=dpg.mvThemeCat_Plots)
                dpg.add_theme_color(dpg.mvPlotCol_MarkerOutline, [150, 255, 0, 255], category=dpg.mvThemeCat_Plots)
                dpg.add_theme_color(dpg.mvPlotCol_Line, [150, 255, 0, 255], category=dpg.mvThemeCat_Plots)
                dpg.add_theme_style(dpg.mvPlotStyleVar_Marker, dpg.mvPlotMarker_Plus, category=dpg.mvThemeCat_Plots)
                dpg.add_theme_style(dpg.mvPlotStyleVar_MarkerSize, 15, category=dpg.mvThemeCat_Plots)
        
        with dpg.theme(tag="peak_ends_theme"):
            with dpg.theme_component(dpg.mvScatterSeries):
                dpg.add_theme_color(dpg.mvPlotCol_MarkerFill, [217, 95, 2, 255], category=dpg.mvThemeCat_Plots)
                dpg.add_theme_color(dpg.mvPlotCol_MarkerOutline, [217, 95, 2, 255], category=dpg.mvThemeCat_Plots)
                dpg.add_theme_color(dpg.mvPlotCol_Line, [217, 95, 2, 255], category=dpg.mvThemeCat_Plots)
                dpg.add_theme_style(dpg.mvPlotStyleVar_Marker, dpg.mvPlotMarker_Plus, category=dpg.mvThemeCat_Plots)
                dpg.add_theme_style(dpg.mvPlotStyleVar_MarkerSize, 15, category=dpg.mvThemeCat_Plots)
        
        # Bind themes to scatter series
        dpg.bind_item_theme("peak_starts_scatter", "peak_starts_theme")
        dpg.bind_item_theme("peak_ends_scatter", "peak_ends_theme")
        # dpg.set_value("persistent_line_series", [[],[]])

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
                        with dpg.menu(label="FLZ"):
                            dpg.add_menu_item(label="Add File", callback=self._add_flz_file)
                            dpg.add_menu_item(label="Add Folder", callback=self._add_flz_folder)
                        with dpg.menu(label="FLR"):
                            dpg.add_menu_item(label="Add File", callback=self._add_flr_file)
                            dpg.add_menu_item(label="Add Folder", callback=self._add_flr_folder)
                        with dpg.menu(label="FLB"):
                            dpg.add_menu_item(label="Add File", callback=self._add_flb_file)
                            dpg.add_menu_item(label="Add Folder", callback=self._add_flb_folder)
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

                    with dpg.menu(label="Database"):
                        dpg.add_menu_item(label="Import Database", callback=self._import_database)
                        dpg.add_menu_item(label="Export Database", callback=self._export_database)
                        dpg.add_separator()
                        dpg.add_menu_item(label="Refresh Table", callback=self._refresh_table)
                        dpg.add_menu_item(label="Database Info", callback=self._show_database_info)
                        dpg.add_separator()
                        dpg.add_menu_item(label="Export to CSV", callback=self._export_database_csv)

                    with dpg.menu(label="Plugins"):
                        # This could be populated by the plugin manager
                        pass
                
                
                # Progress bar in menu bar (ensure it has proper width)
                self.progress_bar.create("menu_bar")
                self.progress_bar.set_progress(0.0)  # Start with 0% progress
                self.progress_bar.hide()  # Start hidden
                
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

    # FLZ File Operations
    def _add_flz_file(self):
        """Open file dialog to add single FLZ file."""
        self.file_dialogs.show_file_dialog(
            title="Select FLZ File",
            callback=self._process_flz_file,
            extensions=[".flz"],
            multiple=False
        )

    def _add_flz_folder(self):
        """Open folder dialog to add all FLZ files from a folder."""
        self.file_dialogs.show_folder_dialog(
            title="Select Folder with FLZ Files",
            callback=self._process_flz_folder
        )

    def _process_flz_file(self, file_path):
        """Process a single FLZ file through DataManager."""
        try:
            self.status_bar.set_status("Adding FLZ file...")
            file_id = self.app.data_manager.add_flz_file(file_path)
            self.status_bar.set_status(f"Added FLZ file: {file_id}")
            self._refresh_table()
        except Exception as e:
            self.status_bar.set_status(f"Error adding FLZ file: {str(e)}")
            print(f"Error processing FLZ file {file_path}: {e}")

    def _process_flz_folder(self, folder_path):
        """Process all FLZ files in a folder with progress tracking."""
        import os
        try:
            self.status_bar.set_status("Scanning FLZ folder...")
            
            # Get list of FLZ files
            flz_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.flz')]
            total_files = len(flz_files)
            
            if total_files == 0:
                self.status_bar.set_status("No FLZ files found in folder")
                return
            
            # Show progress bar
            self.progress_bar.show()
            self.progress_bar.set_progress(0.0)
            self.progress_bar.set_overlay("Adding FLZ files...")
            
            added_count = 0
            
            for i, filename in enumerate(flz_files):
                file_path = os.path.join(folder_path, filename)
                
                # Update progress
                progress = (i + 1) / total_files
                self.progress_bar.set_progress(progress)
                self.progress_bar.set_overlay(f"FLZ: {i + 1}/{total_files}")
                self.status_bar.set_status(f"Processing FLZ files... ({i + 1}/{total_files})")
                
                try:
                    file_id = self.app.data_manager.add_flz_file(file_path)
                    added_count += 1
                    print(f"Added FLZ file: {file_id}")
                except Exception as e:
                    print(f"Error processing {filename}: {e}")
            
            # Hide progress bar and show completion
            self.progress_bar.hide()
            self.status_bar.set_status(f"Added {added_count} FLZ files")
            self._refresh_table()
            
        except Exception as e:
            self.progress_bar.hide()
            self.status_bar.set_status(f"Error processing FLZ folder: {str(e)}")
            print(f"Error processing FLZ folder {folder_path}: {e}")

    # FLR File Operations
    def _add_flr_file(self):
        """Open file dialog to add single FLR file."""
        self.file_dialogs.show_file_dialog(
            title="Select FLR File",
            callback=self._process_flr_file,
            extensions=[".flr"],
            multiple=False
        )

    def _add_flr_folder(self):
        """Open folder dialog to add all FLR files from a folder."""
        self.file_dialogs.show_folder_dialog(
            title="Select Folder with FLR Files",
            callback=self._process_flr_folder
        )

    def _process_flr_file(self, file_path):
        """Process a single FLR file through DataManager."""
        try:
            self.status_bar.set_status("Adding FLR file...")
            file_id = self.app.data_manager.add_flr_file(file_path)
            self.status_bar.set_status(f"Added FLR file: {file_id}")
            self._refresh_table()
        except Exception as e:
            self.status_bar.set_status(f"Error adding FLR file: {str(e)}")
            print(f"Error processing FLR file {file_path}: {e}")

    def _process_flr_folder(self, folder_path):
        """Process all FLR files in a folder with progress tracking."""
        import os
        try:
            self.status_bar.set_status("Scanning FLR folder...")
            
            # Get list of FLR files
            flr_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.flr')]
            total_files = len(flr_files)
            
            if total_files == 0:
                self.status_bar.set_status("No FLR files found in folder")
                return
            
            # Show progress bar
            self.progress_bar.show()
            self.progress_bar.set_progress(0.0)
            self.progress_bar.set_overlay("Adding FLR files...")
            
            added_count = 0
            
            for i, filename in enumerate(flr_files):
                file_path = os.path.join(folder_path, filename)
                
                # Update progress
                progress = (i + 1) / total_files
                self.progress_bar.set_progress(progress)
                self.progress_bar.set_overlay(f"FLR: {i + 1}/{total_files}")
                self.status_bar.set_status(f"Processing FLR files... ({i + 1}/{total_files})")
                
                try:
                    file_id = self.app.data_manager.add_flr_file(file_path)
                    added_count += 1
                    print(f"Added FLR file: {file_id}")
                except Exception as e:
                    print(f"Error processing {filename}: {e}")
            
            # Hide progress bar and show completion
            self.progress_bar.hide()
            self.status_bar.set_status(f"Added {added_count} FLR files")
            self._refresh_table()
            
        except Exception as e:
            self.progress_bar.hide()
            self.status_bar.set_status(f"Error processing FLR folder: {str(e)}")
            print(f"Error processing FLR folder {folder_path}: {e}")

    # FLB File Operations
    def _add_flb_file(self):
        """Open file dialog to add single FLB file."""
        self.file_dialogs.show_file_dialog(
            title="Select FLB File",
            callback=self._process_flb_file,
            extensions=[".flb"],
            multiple=False
        )

    def _add_flb_folder(self):
        """Open folder dialog to add all FLB files from a folder."""
        self.file_dialogs.show_folder_dialog(
            title="Select Folder with FLB Files",
            callback=self._process_flb_folder
        )

    def _process_flb_file(self, file_path):
        """Process a single FLB file through DataManager."""
        try:
            self.status_bar.set_status("Adding FLB file...")
            file_id = self.app.data_manager.add_flb_file(file_path)
            self.status_bar.set_status(f"Added FLB file: {file_id}")
            self._refresh_table()
        except Exception as e:
            self.status_bar.set_status(f"Error adding FLB file: {str(e)}")
            print(f"Error processing FLB file {file_path}: {e}")

    def _process_flb_folder(self, folder_path):
        """Process all FLB files in a folder with progress tracking."""
        import os
        try:
            self.status_bar.set_status("Scanning FLB folder...")
            
            # Get list of FLB files
            flb_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.flb')]
            total_files = len(flb_files)
            
            if total_files == 0:
                self.status_bar.set_status("No FLB files found in folder")
                return
            
            # Show progress bar
            self.progress_bar.show()
            self.progress_bar.set_progress(0.0)
            self.progress_bar.set_overlay("Adding FLB files...")
            
            added_count = 0
            
            for i, filename in enumerate(flb_files):
                file_path = os.path.join(folder_path, filename)
                
                # Update progress
                progress = (i + 1) / total_files
                self.progress_bar.set_progress(progress)
                self.progress_bar.set_overlay(f"FLB: {i + 1}/{total_files}")
                self.status_bar.set_status(f"Processing FLB files... ({i + 1}/{total_files})")
                
                try:
                    file_id = self.app.data_manager.add_flb_file(file_path)
                    added_count += 1
                    print(f"Added FLB file: {file_id}")
                except Exception as e:
                    print(f"Error processing {filename}: {e}")
            
            # Hide progress bar and show completion
            self.progress_bar.hide()
            self.status_bar.set_status(f"Added {added_count} FLB files")
            self._refresh_table()
            
        except Exception as e:
            self.progress_bar.hide()
            self.status_bar.set_status(f"Error processing FLB folder: {str(e)}")
            print(f"Error processing FLB folder {folder_path}: {e}")

    # Database Operations
    def _refresh_table(self):
        """Refresh the table with current database records."""
        try:
            self.status_bar.set_status("Refreshing table...")
            
            # Get all files from database
            files_data = self.app.data_manager.list_files()
            
            if files_data is not None and isinstance(files_data, pd.DataFrame) and not files_data.empty:
                self.table_viewer.load_database_records(files_data)
                self.status_bar.set_status(f"Table updated with {len(files_data)} records")
            else:
                # Create empty dataframe with proper columns
                empty_df = pd.DataFrame(columns=["File ID", "File Name", "File Type", "Date Added", "File Size", "Status"])
                self.table_viewer.load_database_records(empty_df)
                self.status_bar.set_status("No records found in database")
                
        except Exception as e:
            self.status_bar.set_status(f"Error refreshing table: {str(e)}")
            print(f"Error refreshing table: {e}")

    def _show_database_info(self):
        """Show database information in a popup window."""
        try:
            db_info = self.app.data_manager.get_database_info()
            
            # Create or update database info window
            if dpg.does_item_exist("db_info_window"):
                dpg.delete_item("db_info_window")
                
            with dpg.window(label="Database Information", tag="db_info_window", 
                           width=400, height=300, modal=True, show=True):
                dpg.add_text("Database Information", color=[100, 200, 255])
                dpg.add_separator()
                
                for key, value in db_info.items():
                    with dpg.group(horizontal=True):
                        dpg.add_text(f"{key}:", color=[200, 200, 200])
                        dpg.add_spacer(width=10)
                        dpg.add_text(f"{value}", color=[255, 255, 100])
                
                dpg.add_separator()
                dpg.add_button(label="Close", callback=lambda: dpg.delete_item("db_info_window"))
                
        except Exception as e:
            self.status_bar.set_status(f"Error getting database info: {str(e)}")
            print(f"Error getting database info: {e}")

    def _export_database_csv(self):
        """Export database records to CSV file."""
        try:
            files_data = self.app.data_manager.list_files()
            
            if files_data is not None and not files_data.empty:
                # Show save dialog
                self.file_dialogs.show_save_dialog(
                    title="Export Database to CSV",
                    callback=lambda path: self._save_database_csv(files_data, path),
                    default_filename="fldb_export.csv",
                    extensions=[".csv"]
                )
            else:
                self.status_bar.set_status("No data to export")
                
        except Exception as e:
            self.status_bar.set_status(f"Error exporting database: {str(e)}")
            print(f"Error exporting database: {e}")

    def _save_database_csv(self, data, file_path):
        """Save database data to CSV file."""
        try:
            data.to_csv(file_path, index=False)
            self.status_bar.set_status(f"Database exported to: {file_path}")
        except Exception as e:
            self.status_bar.set_status(f"Error saving CSV: {str(e)}")
            print(f"Error saving CSV to {file_path}: {e}")
    
    def _import_database(self):
        """Import a database file using file dialog."""
        try:
            self.file_dialogs.show_file_dialog(
                title="Import Database File",
                callback=lambda file_path: self.app.import_database(file_path),
                extensions=[".fldb"],
                multiple=False
            )
        except Exception as e:
            self.status_bar.set_status(f"Error importing database: {str(e)}")
            print(f"Error importing database: {e}")
    
    def _export_database(self):
        """Export current database to a file using file dialog."""
        try:
            if not self.app.data_manager.db_path:
                self.status_bar.set_status("No database currently open to export")
                return
            
            self.file_dialogs.show_save_dialog(
                title="Export Database File",
                callback=lambda path: self.app.export_database(path),
                default_filename="exported_database.fldb",
                extensions=[".fldb"]
            )
        except Exception as e:
            self.status_bar.set_status(f"Error exporting database: {str(e)}")
            print(f"Error exporting database: {e}")
