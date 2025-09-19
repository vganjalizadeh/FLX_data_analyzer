import dearpygui.dearpygui as dpg
import pandas as pd
import numpy as np
from .theme import create_plot_themes
from ..analysis.signal_processing import deadtime_correction

# Try to import FLR reading tools
try:
    import pyrp
    from ResultsProcessor.Utility import FLBTools, FLRTools
    FLR_TOOLS_AVAILABLE = True
except ImportError:
    FLR_TOOLS_AVAILABLE = False
    print("FLR tools not available - photon data will be read as raw bytes")

class TableViewer:
    def __init__(self, app=None):
        self.app = app
        # Create themes for row selection
        self._create_selection_themes()
        # Initialize plot themes
        self.plot_themes = create_plot_themes()
        self.tag = "data_table"
        self.selected_row = None
        self.selected_row_theme = None
        self.default_row_theme = None
        self.context_menu_row = None  # Track which row the context menu was opened on
        
        # Single plot management
        self.current_photon_data = None
        self.current_file_id = None
        
        self.data = pd.DataFrame(columns=["File name","UPC", "BG [kcps]", "FL [kcps]", "Flowrate [uL/min]", "Signal CV%"])
        for n in range(20):
            self.data.loc[n] = [f"example{n}.flx", f"{123456789012 + n}", 150 - n, 300 + n, 0.5 + n * 0.1, 5.0 + n * 0.5]

    def _create_selection_themes(self):
        """Create themes for selected and default row states."""
        # Theme for selected row
        with dpg.theme() as self.selected_row_theme:
            with dpg.theme_component(dpg.mvTableRow):
                dpg.add_theme_color(dpg.mvThemeCol_TableRowBg, [75, 0, 130, 100])  # Dark purple with transparency
                dpg.add_theme_color(dpg.mvThemeCol_TableRowBgAlt, [85, 10, 140, 100])  # Slightly different purple for alternating
                dpg.add_theme_style(dpg.mvStyleVar_CellPadding, 4, 0, category=dpg.mvThemeCat_Core)  # Proper cell padding
                dpg.add_theme_style(dpg.mvStyleVar_SelectableTextAlign, 0, 0, category=dpg.mvThemeCat_Core)

        # Theme for default row
        with dpg.theme() as self.default_row_theme:
            with dpg.theme_component(dpg.mvTableRow):
                dpg.add_theme_color(dpg.mvThemeCol_TableRowBg, [0, 0, 0, 0])  # Transparent
                dpg.add_theme_color(dpg.mvThemeCol_TableRowBgAlt, [30, 30, 30, 50])  # Default alternating row color
                dpg.add_theme_style(dpg.mvStyleVar_CellPadding, 4, 0, category=dpg.mvThemeCat_Core)  # Proper cell padding
                dpg.add_theme_style(dpg.mvStyleVar_SelectableTextAlign, 0, 0, category=dpg.mvThemeCat_Core)

    def create(self, parent_container):
        """Creates the table within a given parent container."""
        with dpg.table(tag=self.tag, header_row=True, resizable=True, policy=dpg.mvTable_SizingStretchProp,
                       row_background=True, borders_innerV=True, borders_outerV=True, delay_search=True,
                       sortable=True, callback=self._sort_callback, parent=parent_container):
            self.update_data(self.data)

    def _sort_callback(self, sort_specs):

        # sort_specs scenarios:
        #   1. no sorting -> sort_specs == None
        #   2. single sorting -> sort_specs == [[column_id, direction]]
        #   3. multi sorting -> sort_specs == [[column_id, direction], [column_id, direction], ...]
        #
        # notes:
        #   1. direction is ascending if == 1
        #   2. direction is ascending if == -1

        # no sorting case
        if sort_specs is None: 
            return
        
        # Check if sort_specs is empty or malformed
        if not sort_specs or len(sort_specs) == 0:
            return
            
        # Check if first sort spec has the expected structure
        if not isinstance(sort_specs[0], (list, tuple)) or len(sort_specs[0]) < 2:
            return

        rows = dpg.get_item_children(self.tag, 1)

        # create a list that can be sorted based on first cell
        # value, keeping track of row and value used to sort
        sortable_list = []
        for row in rows:
            first_cell = dpg.get_item_children(row, 1)[3]
            sortable_list.append([row, dpg.get_value(first_cell)])

        def _sorter(e):
            return e[1]

        sortable_list.sort(key=_sorter, reverse=sort_specs[0][1] < 0)

        # create list of just sorted row ids
        new_order = []
        for pair in sortable_list:
            new_order.append(pair[0])

        dpg.reorder_items(self.tag, 1, new_order)

    def _on_row_select(self, sender, app_data, user_data):
        """Callback function when a row is selected."""
        row_index = user_data
        
        # Clear previous selection highlighting BEFORE setting new selection
        if self.selected_row is not None:
            self._unhighlight_row(self.selected_row)
        
        # Set new selection
        self.selected_row = row_index
        
        # Highlight new selection
        # self._highlight_row(row_index)
        
        # Update details window with selected row information
        self._update_details_window(row_index)

    def _highlight_row(self, row_index):
        """Highlight the selected row using theme."""
        row_tag = f"row_{row_index}"
        row_selectable_tag = f"row_selectable_{row_index}"
        # if dpg.does_item_exist(row_tag):
        #     # Apply selected row theme to the table row
        #     dpg.bind_item_theme(row_tag, self.selected_row_theme)
        # deselect the selectable
        dpg.bind_item_theme(row_selectable_tag, self.default_row_theme)

        # Also change text color for better visibility
        # for col_idx in range(len(self.data.columns)):
        #     text_tag = f"text_{row_index}_{col_idx}"
            # if dpg.does_item_exist(text_tag):
            #     dpg.configure_item(text_tag, color=[255, 255, 100])  # Yellow text

    def _unhighlight_row(self, row_index):
        """Remove highlight from a specific row using theme."""
        row_tag = f"row_{row_index}"
        row_selectable_tag = f"row_selectable_{row_index}"
        
        if dpg.does_item_exist(row_tag):
            # Apply default row theme to the table row
            dpg.set_value(row_selectable_tag, False)
        
        # Note: Don't apply table row theme to selectable - selectables need their own theme
        # The selectable will use its default appearance when not selected

        # # Reset text color to default
        # for col_idx in range(len(self.data.columns)):
        #     text_tag = f"text_{row_index}_{col_idx}"
        #     if dpg.does_item_exist(text_tag):
        #         dpg.configure_item(text_tag, color=[255, 255, 255])  # Default white

    def _update_details_window(self, row_index):
        """Update the details window with information from the selected row."""
        if row_index is None or row_index >= len(self.data):
            return
        
        # Check if we're displaying database records
        if hasattr(self, 'database_records') and not self.database_records.empty:
            self._update_details_window_with_db_record(row_index)
            return
        
        # Hide placeholder text
        if dpg.does_item_exist("details_placeholder"):
            dpg.hide_item("details_placeholder")
            
        # Clear existing details content
        if dpg.does_item_exist("details_content"):
            dpg.delete_item("details_content")
        
        # Create new details content for regular data
        with dpg.group(tag="details_content", parent="details_window"):
            dpg.add_text(f"Selected Row: {row_index + 1}", color=[100, 200, 255])
            dpg.add_separator()
            
            # Display each column value in a formatted way
            row_data = self.data.iloc[row_index]
            for col_name, value in row_data.items():
                with dpg.group(horizontal=True):
                    dpg.add_text(f"{col_name}:", color=[200, 200, 200])
                    dpg.add_spacer(width=10)
                    dpg.add_text(f"{value}", color=[255, 255, 100])  # Yellow color for values
            
            dpg.add_separator()
            dpg.add_text(f"DataFrame Index: {row_index}", color=[150, 150, 150])
            
        # Show the details window if it's hidden
        if not dpg.is_item_shown("details_window"):
            dpg.show_item("details_window")

    def update_data(self, dataframe):
        if dataframe is None:
            return

        dataframe = dataframe.round(2)
        
        # Clear existing table content
        dpg.delete_item(self.tag, children_only=True)

        # Add new columns
        for col in dataframe.columns:
            dpg.add_table_column(label=col, parent=self.tag)

        # Add new rows with selection capability
        for index, row in dataframe.iterrows():
            # print(index, row)
            with dpg.table_row(parent=self.tag, tag=f"row_{index}"):
                # Add text items for each column
                for col_idx, item in enumerate(row[:-1]):
                    text_tag = f"text_{index}_{col_idx}"
                    dpg.add_text(str(item), tag=text_tag)

                # Add click handler to the entire row
                selectable_tag = f"row_selectable_{index}"
                dpg.add_selectable(label=f"{row[-1]}", span_columns=True, callback=self._on_row_select, user_data=index, tag=selectable_tag)
                
                # Add right-click context menu to the selectable
                self._create_context_menu(index, selectable_tag)
                
            dpg.bind_item_theme(f"row_{index}", self.default_row_theme)

    def load_database_records(self, records_df):
        """Load database records into the table with proper formatting."""
        if records_df is None or records_df.empty:
            # Show empty table with appropriate columns (replace File ID with Row)
            empty_df = pd.DataFrame(columns=["Row", "File Name", "File Type", "Date Added", "File Size", "Status"])
            self.data = empty_df
            self.update_data(empty_df)
            return
        
        # Store original data for row selection details (keep File ID for operations)
        self.database_records = records_df
        
        # Create display version with row numbers instead of File ID
        display_df = records_df.copy()
        display_df = display_df.drop(columns=['File ID'])
        display_df.insert(0, 'Row', range(1, len(display_df) + 1))
        
        # Store display data and update table
        self.data = display_df
        self.update_data(display_df)
        
        print(f"Loaded {len(records_df)} database records into table")

    def _update_details_window_with_db_record(self, row_index):
        """Update the details window with database record information using tabs."""
        if (row_index is None or 
            not hasattr(self, 'database_records') or 
            row_index >= len(self.database_records)):
            return
        
        # Hide placeholder text
        if dpg.does_item_exist("details_placeholder"):
            dpg.hide_item("details_placeholder")
            
        # Clear existing details content
        if dpg.does_item_exist("details_content"):
            dpg.delete_item("details_content")
        
        # Get the database record
        record = self.database_records.iloc[row_index]
        file_id = record.get('file_id', record.get('File ID', ''))
        
        # Create new details content without tabs - linear layout
        with dpg.group(tag="details_content", parent="details_window"):
            # File Information and Statistics side by side at the top
            with dpg.group(horizontal=True):
                # File Information Section (left side)
                with dpg.group():
                    dpg.add_text("File Information:", color=[200, 200, 100])
                    dpg.add_spacer(height=5)
                    
                    # Display basic file information in a more compact format
                    for col_name, value in record.items():
                        with dpg.group(horizontal=True):
                            dpg.add_text(f"{col_name}:", color=[200, 200, 200])
                            dpg.add_spacer(width=10)
                            dpg.add_text(f"{value}", color=[255, 255, 100])
                
                # Add some spacing between sections
                dpg.add_spacer(width=30)
                
                # Statistics Section (right side) - will be populated when data loads
                with dpg.group(tag="local_statistics_group"):
                    dpg.add_text("Statistics:", color=[150, 200, 150])
                    dpg.add_spacer(height=5)
                    with dpg.group(horizontal=True):
                        dpg.add_text("Avg Rate:", color=[200, 200, 200])
                        dpg.add_text("Loading...", color=[255, 255, 100], tag="local_avg_rate_text")
                    with dpg.group(horizontal=True):
                        dpg.add_text("Std Dev:", color=[200, 200, 200])
                        dpg.add_text("Loading...", color=[255, 255, 100], tag="local_std_rate_text")
                    with dpg.group(horizontal=True):
                        dpg.add_text("Min Rate:", color=[200, 200, 200])
                        dpg.add_text("Loading...", color=[255, 255, 100], tag="local_min_rate_text")
                    with dpg.group(horizontal=True):
                        dpg.add_text("Max Rate:", color=[200, 200, 200])
                        dpg.add_text("Loading...", color=[255, 255, 100], tag="local_max_rate_text")
            
            dpg.add_separator()
            dpg.add_spacer(height=10)
            
            # Load detailed file data (photon data will go to persistent plot)
            if file_id and self.app:
                self._add_detailed_file_analysis(file_id)
            else:
                dpg.add_text("No detailed data available", color=[255, 100, 100])
        
        # Show the details window if it's hidden
        if not dpg.is_item_shown("details_window"):
            dpg.show_item("details_window")

    def _add_detailed_file_analysis(self, file_id):
        """Add detailed file analysis including plots, statistics, and images."""
        try:
            # Get file data from database
            file_data = self.app.get_file_data(file_id)
            if not file_data:
                dpg.add_text("No detailed data available", color=[255, 100, 100])
                return
            
            # Update persistent plot with new data (this will show statistics and plot controls above)
            self._load_photon_data_to_persistent_plot(file_data, file_id)
            
            # Add images below the persistent plot (they will appear in the details content area) 
            self._add_image_display(file_data, file_id)
            
        except Exception as e:
            dpg.add_text(f"Error loading detailed data: {str(e)}", color=[255, 100, 100])
            print(f"Error in detailed file analysis: {e}")

    def _add_photon_data_analysis(self, file_data, file_id=None):
        """Add photon data plot and statistics."""
        try:
            photon_data = None
            
            # Get file_id for unique tags
            if file_id is None:
                file_id = file_data.get('file_id', 'unknown') if isinstance(file_data, dict) else 'unknown'
            
            # Try to get photon data from the file_data structure
            if isinstance(file_data, dict):
                if 'raw_data' in file_data and 'photon_data' in file_data['raw_data']:
                    photon_data = file_data['raw_data']['photon_data']
                elif 'photon_data' in file_data:
                    photon_data = file_data['photon_data']
            
            if photon_data is not None:
                dpg.add_text("Photon Data Analysis:", color=[200, 200, 100])
                
                # Process photon data for display
                photon_data = self._process_photon_data_for_display(photon_data)
                
                if photon_data is None:
                    dpg.add_text("Could not process photon data", color=[255, 100, 100])
                    return
                
                # Calculate statistics
                if len(photon_data) > 0:
                    avg_rate = np.mean(photon_data) * 1e3  # Convert to kcps
                    std_rate = np.std(photon_data) * 1e3  # Convert to kcps
                    min_rate = np.min(photon_data)
                    max_rate = np.max(photon_data)
                    
                    # Display statistics
                    with dpg.group():
                        dpg.add_text("Statistics:", color=[150, 200, 150])
                        with dpg.group(horizontal=True):
                            dpg.add_text("Avg Rate:", color=[200, 200, 200])
                            dpg.add_text(f"{avg_rate:.2f} kcps", color=[255, 255, 100])
                        with dpg.group(horizontal=True):
                            dpg.add_text("Std Dev:", color=[200, 200, 200])
                            dpg.add_text(f"{std_rate:.2f} kcps", color=[255, 255, 100])
                        with dpg.group(horizontal=True):
                            dpg.add_text("Min Rate:", color=[200, 200, 200])
                            dpg.add_text(f"{min_rate:.2f} Mcps", color=[255, 255, 100])
                        with dpg.group(horizontal=True):
                            dpg.add_text("Max Rate:", color=[200, 200, 200])
                            dpg.add_text(f"{max_rate:.2f} Mcps", color=[255, 255, 100])
                    
                    dpg.add_spacer(height=10)
                    
                    # Add controls for deadtime correction and rebin value
                    dpg.add_text("Plot Controls:", color=[150, 200, 150])
                    with dpg.group(horizontal=True):
                        # Deadtime correction checkbox
                        deadtime_checkbox_tag = f"deadtime_checkbox_{file_id}"
                        dpg.add_checkbox(label="Deadtime Correction", default_value=True, tag=deadtime_checkbox_tag,
                                       callback=lambda: self._update_photon_plot(file_id, photon_data))
                        
                        # Rebin value input
                        dpg.add_spacer(width=20)
                        dpg.add_text("Rebin (us):", color=[200, 200, 200])
                        rebin_input_tag = f"rebin_input_{file_id}"
                        dpg.add_input_int(default_value=5, width=100, tag=rebin_input_tag, min_value=1, max_value=1000,
                                        callback=lambda: self._update_photon_plot(file_id, photon_data), on_enter=True)
                    
                    dpg.add_spacer(height=10)
                    
                    # Create plot container
                    plot_container_tag = f"photon_plot_container_{file_id}"
                    with dpg.group(tag=plot_container_tag):
                        pass
                    
                    # Initial plot creation
                    self._update_photon_plot(file_id, photon_data)
                else:
                    dpg.add_text("No photon data points available", color=[255, 100, 100])
            else:
                dpg.add_text("No photon data available", color=[200, 200, 200])
                
        except Exception as e:
            dpg.add_text(f"Error analyzing photon data: {str(e)}", color=[255, 100, 100])
            print(f"Error in photon data analysis: {e}")
        
        # Note: Photon data analysis is now handled by the persistent plot above

    def _add_image_display(self, file_data, file_id=None):
        """Add image display for alignment and laser on images side by side."""
        try:
            dpg.add_spacer(height=10)
            dpg.add_text("Images:", color=[200, 200, 100])
            
            # Try to get images from file_data
            alignment_image = None
            laser_on_image = None
            
            if isinstance(file_data, dict):
                if 'raw_data' in file_data:
                    raw_data = file_data['raw_data']
                    alignment_image = raw_data.get('alignment_image')
                    laser_on_image = raw_data.get('laser_on_image')
                else:
                    alignment_image = file_data.get('alignment_image')
                    laser_on_image = file_data.get('laser_on_image')
            
            # Get file_id for unique tags
            if file_id is None:
                file_id = file_data.get('file_id', 'unknown') if isinstance(file_data, dict) else 'unknown'
            
            # Display images side by side
            with dpg.group(horizontal=True):
                # Left side - Alignment Image
                with dpg.group():
                    # dpg.add_text("Alignment Image", color=[150, 200, 150])
                    if alignment_image is not None:
                        self._display_image_optimized(alignment_image, f"alignment_img_{file_id}", label="Alignment Image")
                    else:
                        dpg.add_text("Not available", color=[200, 200, 200])
                
                dpg.add_spacer(width=20)
                
                # Right side - Laser On Image
                with dpg.group():
                    # dpg.add_text("Laser On Image", color=[150, 200, 150])
                    if laser_on_image is not None:
                        self._display_image_optimized(laser_on_image, f"laser_img_{file_id}", label="Laser On Image")
                    else:
                        dpg.add_text("Not available", color=[200, 200, 200])
                
        except Exception as e:
            dpg.add_text(f"Error displaying images: {str(e)}", color=[255, 100, 100])
            print(f"Error in image display: {e}")

    def _display_image_optimized(self, image_data, unique_tag, label=""):
        """Display an image in an interactive plot with zoom and pan capabilities."""
        try:
            import numpy as np
            
            # Handle different image data formats
            if isinstance(image_data, str):
                # If stored as JSON string, try to parse
                import json
                try:
                    image_data = json.loads(image_data)
                    if image_data is None:
                        dpg.add_text("Not available", color=[200, 200, 200])
                        return
                except:
                    dpg.add_text("Could not parse image data", color=[255, 100, 100])
                    return
            
            if image_data is None:
                dpg.add_text("Not available", color=[200, 200, 200])
                return
            
            # Convert to numpy array if needed
            if isinstance(image_data, (list, tuple)):
                image_data = np.array(image_data)
            
            if isinstance(image_data, np.ndarray) and image_data.size > 0:
                # Handle different image shapes
                if len(image_data.shape) == 1:
                    # Assume square grayscale image
                    size = int(np.sqrt(len(image_data)))
                    if size * size == len(image_data):
                        image_data = image_data.reshape((size, size))
                    else:
                        dpg.add_text("Invalid image dimensions", color=[255, 100, 100])
                        return
                
                # Get image dimensions
                if len(image_data.shape) == 2:
                    height, width = image_data.shape
                    channels = 1
                elif len(image_data.shape) == 3:
                    height, width, channels = image_data.shape
                else:
                    dpg.add_text("Unsupported image format", color=[255, 100, 100])
                    return
                
                # Create texture for the image
                texture_tag = f"texture_{unique_tag}"
                if dpg.does_item_exist(texture_tag):
                    dpg.delete_item(texture_tag)
                
                # Normalize data to 0-1 range for display
                if image_data.dtype != np.float32:
                    image_data = image_data.astype(np.float32)
                
                if image_data.max() > 1.0:
                    image_data = image_data / 255.0  # Normalize uint8 to [0,1]
                
                # Handle different image formats
                if len(image_data.shape) == 2:
                    # Grayscale image - convert to RGBA
                    rgba_data = np.zeros((height, width, 4), dtype=np.float32)
                    rgba_data[:, :, 0] = image_data  # R
                    rgba_data[:, :, 1] = image_data  # G
                    rgba_data[:, :, 2] = image_data  # B
                    rgba_data[:, :, 3] = 1.0        # A
                elif len(image_data.shape) == 3:
                    if channels == 3:
                        # RGB image - add alpha channel
                        rgba_data = np.zeros((height, width, 4), dtype=np.float32)
                        rgba_data[:, :, :3] = image_data  # RGB
                        rgba_data[:, :, 3] = 1.0         # A (full opacity)
                    elif channels == 4:
                        # RGBA image - use as is
                        rgba_data = image_data
                    else:
                        dpg.add_text(f"Unsupported channel count: {channels}", color=[255, 100, 100])
                        return
                
                # Flatten and convert to array format like in the example
                import array
                texture_data = rgba_data.flatten()
                raw_data = array.array('f', texture_data)
                
                with dpg.texture_registry():
                    dpg.add_raw_texture(width=width, height=height, default_value=raw_data, 
                                      format=dpg.mvFormat_Float_rgba, tag=texture_tag)
                
                # Create an interactive plot for the image
                plot_tag = f"image_plot_{unique_tag}"
                if dpg.does_item_exist(plot_tag):
                    dpg.delete_item(plot_tag)
                
                with dpg.plot(label=label, height=400, width=400, tag=plot_tag, equal_aspects=True):
                    
                    # X-axis (image width) 
                    x_axis = dpg.add_plot_axis(dpg.mvXAxis, label="X (pixels)")
                    
                    # Y-axis (image height)
                    with dpg.plot_axis(dpg.mvYAxis, label="Y (pixels)") as y_axis:
                        # Add the image as an image series - DearPyGui will handle interaction automatically
                        dpg.add_image_series(texture_tag, [0, 0], [width, height], 
                                           label=f"Image", parent=y_axis, tag=f"image_series_{unique_tag}")
                
                # Apply image plot theme
                dpg.bind_item_theme(plot_tag, self.plot_themes['image_plot'])
                
                # Add image info
                shape_info = f"{width}x{height}"
                if channels > 1:
                    if channels == 3:
                        shape_info += " (RGB)"
                    elif channels == 4:
                        shape_info += " (RGBA)"
                    else:
                        shape_info += f"x{channels}"
                
            else:
                dpg.add_text("No image data", color=[200, 200, 200])
                
        except Exception as e:
            dpg.add_text(f"Error displaying image: {str(e)}", color=[255, 100, 100])
            print(f"Error displaying image: {e}")
            import traceback
            traceback.print_exc()

    def _read_flr_data(self, flr_file_path):
        """Read FLR data using the provided tools or fallback method."""
        try:
            if FLR_TOOLS_AVAILABLE:
                # Use the provided FLR tools
                data = FLRTools.ReadFLRData(flr_file_path)
                return data
            else:
                # Fallback: read as raw bytes
                with open(flr_file_path, 'rb') as f:
                    raw_bytes = f.read()
                    # Convert bytes to numpy array (each byte is a datapoint)
                    photon_data = np.frombuffer(raw_bytes, dtype=np.uint8)
                    return photon_data
        except Exception as e:
            print(f"Error reading FLR data from {flr_file_path}: {e}")
            return None

    def _process_photon_data_for_display(self, photon_data):
        """Process photon data for display - handle different data formats."""
        try:
            if photon_data is None:
                return None
            
            # Handle different data types
            if isinstance(photon_data, str):
                # Try to parse JSON
                import json
                try:
                    photon_data = json.loads(photon_data)
                except:
                    return None
            
            if isinstance(photon_data, (list, tuple)):
                photon_data = np.array(photon_data)
            
            if isinstance(photon_data, np.ndarray):
                # Convert to float for statistics
                if photon_data.dtype == np.uint8:
                    # Each byte represents photons/us, might need scaling
                    return photon_data.astype(np.float32)
                return photon_data.astype(np.float32)
            
            return None
        except Exception as e:
            print(f"Error processing photon data: {e}")
            return None

    def _view_file_data(self, file_id):
        """View detailed file data from database."""
        try:
            if not self.app:
                print("No app reference available")
                return
            
            file_data = self.app.get_file_data(file_id)
            if file_data:
                self._show_file_data_window(file_id, file_data)
            else:
                print(f"No data found for file ID: {file_id}")
        except Exception as e:
            print(f"Error viewing file data: {e}")

    def _show_file_data_window(self, file_id, file_data):
        """Show detailed file data in a popup window."""
        window_tag = f"file_data_window_{file_id}"
        
        # Close existing window if open
        if dpg.does_item_exist(window_tag):
            dpg.delete_item(window_tag)
        
        with dpg.window(label=f"File Data - {file_id}", tag=window_tag,
                       width=600, height=400, modal=True, show=True):
            dpg.add_text(f"File ID: {file_id}", color=[100, 200, 255])
            dpg.add_separator()
            
            # Display file data based on type
            if isinstance(file_data, dict):
                for key, value in file_data.items():
                    if isinstance(value, (dict, list)):
                        dpg.add_text(f"{key}:", color=[200, 200, 100])
                        dpg.add_text(f"  {str(value)[:200]}...", color=[200, 200, 200], wrap=550)
                    else:
                        with dpg.group(horizontal=True):
                            dpg.add_text(f"{key}:", color=[200, 200, 100])
                            dpg.add_spacer(width=10)
                            dpg.add_text(f"{value}", color=[255, 255, 100])
            else:
                dpg.add_text(f"Data: {str(file_data)}", color=[255, 255, 100], wrap=550)
            
            dpg.add_separator()
            dpg.add_button(label="Close", callback=lambda: dpg.delete_item(window_tag))

    def _export_record(self, file_id):
        """Export a specific record."""
        try:
            if not self.app:
                print("No app reference available")
                return
            
            # Get the record data
            if hasattr(self, 'database_records'):
                record = self.database_records[self.database_records['File ID'] == file_id]
                if not record.empty:
                    # Use file dialogs to save
                    if hasattr(self.app, 'main_window') and hasattr(self.app.main_window, 'file_dialogs'):
                        self.app.main_window.file_dialogs.show_save_dialog(
                            title=f"Export Record {file_id}",
                            callback=lambda path: self._save_record_to_file(record, path),
                            default_filename=f"record_{file_id}.csv",
                            extensions=[".csv", ".json"]
                        )
                    else:
                        print(f"Cannot export record - file dialogs not available")
                else:
                    print(f"Record with ID {file_id} not found")
            else:
                print("No database records loaded")
        except Exception as e:
            print(f"Error exporting record: {e}")

    def _save_record_to_file(self, record, file_path):
        """Save record data to file."""
        try:
            if file_path.lower().endswith('.json'):
                record.to_json(file_path, orient='records', indent=2)
            else:
                record.to_csv(file_path, index=False)
            print(f"Record exported to: {file_path}")
        except Exception as e:
            print(f"Error saving record to {file_path}: {e}")

    def _create_context_menu(self, row_index, parent_item):
        """Create a right-click context menu for table rows."""
        menu_tag = f"context_menu_{row_index}"
        
        # Delete existing menu if it exists
        if dpg.does_item_exist(menu_tag):
            dpg.delete_item(menu_tag)
        
        # Get row data to determine if it's a database record
        is_database_record = hasattr(self, 'database_records') and not self.database_records.empty
        
        with dpg.popup(parent_item, tag=menu_tag, mousebutton=dpg.mvMouseButton_Right):
            if is_database_record:
                # Context menu for database records
                dpg.add_menu_item(label="Delete Record", callback=self._delete_record, user_data=row_index)
                dpg.add_menu_item(label="Duplicate Record", callback=self._duplicate_record, user_data=row_index)
                dpg.add_separator()
                dpg.add_menu_item(label="Rename File", callback=self._rename_file, user_data=row_index)
                dpg.add_separator()
                dpg.add_menu_item(label="View Details", callback=self._view_record_details, user_data=row_index)
                dpg.add_menu_item(label="Export Record", callback=self._export_record_context, user_data=row_index)
            else:
                # Context menu for regular data
                dpg.add_menu_item(label="Delete Row", callback=self._delete_row, user_data=row_index)
                dpg.add_menu_item(label="Duplicate Row", callback=self._duplicate_row, user_data=row_index)
                dpg.add_separator()
                dpg.add_menu_item(label="View Details", callback=self._view_row_details, user_data=row_index)

    def _delete_record(self, sender, app_data, user_data):
        """Delete a database record."""
        row_index = user_data
        try:
            if (hasattr(self, 'database_records') and 
                not self.database_records.empty and 
                row_index < len(self.database_records)):
                
                record = self.database_records.iloc[row_index]
                file_id = record.get('file_id', record.get('File ID', ''))
                file_name = record.get('file_name', record.get('File Name', 'Unknown'))
                
                # Show confirmation dialog
                self._show_delete_confirmation(file_id, file_name, row_index)
        except Exception as e:
            print(f"Error deleting record: {e}")

    def _show_delete_confirmation(self, file_id, file_name, row_index):
        """Show confirmation dialog for delete operation."""
        dialog_tag = "delete_confirmation_dialog"
        
        # Delete existing dialog if it exists
        if dpg.does_item_exist(dialog_tag):
            dpg.delete_item(dialog_tag)
        
        with dpg.window(label="Confirm Delete", tag=dialog_tag, width=400, height=150, modal=True, show=True):
            dpg.add_text(f"Are you sure you want to delete this record?")
            dpg.add_text(f"File: {file_name}", color=[255, 255, 100])
            dpg.add_text(f"ID: {file_id}", color=[150, 150, 150])
            dpg.add_separator()
            
            with dpg.group(horizontal=True):
                dpg.add_button(label="Delete", callback=self._confirm_delete, 
                             user_data={'file_id': file_id, 'row_index': row_index}, 
                             width=100)
                dpg.add_same_line()
                dpg.add_button(label="Cancel", callback=lambda: dpg.delete_item(dialog_tag), width=100)

    def _confirm_delete(self, sender, app_data, user_data):
        """Actually delete the record after confirmation."""
        try:
            file_id = user_data['file_id']
            row_index = user_data['row_index']
            
            if self.app and hasattr(self.app, 'delete_file'):
                success = self.app.delete_file(file_id)
                if success:
                    print(f"Successfully deleted record: {file_id}")
                    # Refresh the table
                    self._refresh_table_data()
                else:
                    print(f"Failed to delete record: {file_id}")
            
            # Close confirmation dialog
            dpg.delete_item("delete_confirmation_dialog")
            
        except Exception as e:
            print(f"Error confirming delete: {e}")

    def _duplicate_record(self, sender, app_data, user_data):
        """Duplicate a database record."""
        row_index = user_data
        try:
            if (hasattr(self, 'database_records') and 
                not self.database_records.empty and 
                row_index < len(self.database_records)):
                
                record = self.database_records.iloc[row_index]
                file_id = record.get('file_id', record.get('File ID', ''))
                
                if self.app and hasattr(self.app, 'duplicate_file'):
                    new_file_id = self.app.duplicate_file(file_id)
                    if new_file_id:
                        print(f"Successfully duplicated record: {file_id} -> {new_file_id}")
                        # Refresh the table
                        self._refresh_table_data()
                    else:
                        print(f"Failed to duplicate record: {file_id}")
                else:
                    print("Duplicate functionality not available")
        except Exception as e:
            print(f"Error duplicating record: {e}")

    def _rename_file(self, sender, app_data, user_data):
        """Rename the file name of a database record."""
        row_index = user_data
        try:
            if (hasattr(self, 'database_records') and 
                not self.database_records.empty and 
                row_index < len(self.database_records)):
                
                record = self.database_records.iloc[row_index]
                file_id = record.get('file_id', record.get('File ID', ''))
                current_name = record.get('file_name', record.get('File Name', ''))
                
                self._show_rename_dialog(file_id, current_name)
        except Exception as e:
            print(f"Error renaming file: {e}")

    def _show_rename_dialog(self, file_id, current_name):
        """Show dialog for renaming a file."""
        dialog_tag = "rename_dialog"
        
        # Delete existing dialog if it exists
        if dpg.does_item_exist(dialog_tag):
            dpg.delete_item(dialog_tag)
        
        with dpg.window(label="Rename File", tag=dialog_tag, width=400, height=150, modal=True, show=True):
            dpg.add_text("Enter new file name:")
            dpg.add_input_text(tag="rename_input", default_value=current_name, width=350)
            dpg.add_separator()
            
            with dpg.group(horizontal=True):
                dpg.add_button(label="Rename", callback=self._confirm_rename, 
                             user_data=file_id, width=100)
                dpg.add_same_line()
                dpg.add_button(label="Cancel", callback=lambda: dpg.delete_item(dialog_tag), width=100)

    def _confirm_rename(self, sender, app_data, user_data):
        """Actually rename the file after confirmation."""
        try:
            file_id = user_data
            new_name = dpg.get_value("rename_input")
            
            if not new_name.strip():
                print("File name cannot be empty")
                return
            
            if self.app and hasattr(self.app, 'rename_file'):
                success = self.app.rename_file(file_id, new_name.strip())
                if success:
                    print(f"Successfully renamed file: {file_id} -> {new_name}")
                    # Refresh the table
                    self._refresh_table_data()
                else:
                    print(f"Failed to rename file: {file_id}")
            else:
                print("Rename functionality not available")
            
            # Close rename dialog
            dpg.delete_item("rename_dialog")
            
        except Exception as e:
            print(f"Error confirming rename: {e}")

    def _delete_row(self, sender, app_data, user_data):
        """Delete a regular data row."""
        row_index = user_data
        try:
            if row_index < len(self.data):
                # Remove the row from the dataframe
                self.data = self.data.drop(self.data.index[row_index]).reset_index(drop=True)
                # Update the table display
                self.update_data(self.data)
                print(f"Deleted row {row_index}")
        except Exception as e:
            print(f"Error deleting row: {e}")

    def _duplicate_row(self, sender, app_data, user_data):
        """Duplicate a regular data row."""
        row_index = user_data
        try:
            if row_index < len(self.data):
                # Get the row to duplicate
                row_to_duplicate = self.data.iloc[row_index].copy()
                
                # Modify the file name to indicate it's a duplicate
                if 'File name' in row_to_duplicate:
                    name = str(row_to_duplicate['File name'])
                    if not name.endswith('_copy'):
                        row_to_duplicate['File name'] = f"{name}_copy"
                
                # Insert the duplicated row after the original
                new_data = pd.concat([
                    self.data.iloc[:row_index+1],
                    pd.DataFrame([row_to_duplicate]),
                    self.data.iloc[row_index+1:]
                ]).reset_index(drop=True)
                
                self.data = new_data
                # Update the table display
                self.update_data(self.data)
                print(f"Duplicated row {row_index}")
        except Exception as e:
            print(f"Error duplicating row: {e}")

    def _view_record_details(self, sender, app_data, user_data):
        """View details of a database record."""
        row_index = user_data
        self._on_row_select(sender, app_data, row_index)

    def _view_row_details(self, sender, app_data, user_data):
        """View details of a regular data row."""
        row_index = user_data
        self._on_row_select(sender, app_data, row_index)

    def _export_record_context(self, sender, app_data, user_data):
        """Export a record from context menu."""
        row_index = user_data
        try:
            if (hasattr(self, 'database_records') and 
                not self.database_records.empty and 
                row_index < len(self.database_records)):
                
                record = self.database_records.iloc[row_index]
                file_id = record.get('file_id', record.get('File ID', ''))
                self._export_record(file_id)
        except Exception as e:
            print(f"Error exporting record from context menu: {e}")

    def _refresh_table_data(self):
        """Refresh the table data from the database."""
        try:
            if self.app and hasattr(self.app, 'get_all_files'):
                updated_records = self.app.get_all_files()
                self.load_database_records(updated_records)
        except Exception as e:
            print(f"Error refreshing table data: {e}")

    def _update_photon_plot(self, file_id, photon_data):
        """Update the photon plot based on current control values."""
        try:
            # Get control values
            deadtime_checkbox_tag = f"deadtime_checkbox_{file_id}"
            rebin_input_tag = f"rebin_input_{file_id}"
            plot_container_tag = f"photon_plot_container_{file_id}"
            
            # Check if controls exist
            if not dpg.does_item_exist(deadtime_checkbox_tag) or not dpg.does_item_exist(rebin_input_tag):
                return
            
            correct_for_deadtime = dpg.get_value(deadtime_checkbox_tag)
            rebin = max(1, dpg.get_value(rebin_input_tag))  # Ensure minimum value of 1
            
            # Process the data
            slice_arr = np.array(list(range(0, len(photon_data), rebin)) + [len(photon_data)])
            plot_data = (np.add.reduceat(photon_data, slice_arr[:-1]) / np.diff(slice_arr)).astype(np.float32)  # in Mcps
            
            if correct_for_deadtime:
                plot_data = deadtime_correction(plot_data, deadtime=29e-9)
            
            x_data = np.arange(len(plot_data)) * rebin * 1e-6  # Convert to seconds
            
            # Clear existing plot
            if dpg.does_item_exist(plot_container_tag):
                dpg.delete_item(plot_container_tag, children_only=True)
            
            # Create new plot
            plot_tag = f"photon_plot_{file_id}"
            with dpg.plot(label=f"Photon Count vs Time (rebinned at {rebin}us)", height=300, width=-1, 
                         tag=plot_tag, parent=plot_container_tag):
                # Set plot background color
                dpg.add_plot_legend()
                dpg.add_plot_axis(dpg.mvXAxis, label="Time (s)")
                with dpg.plot_axis(dpg.mvYAxis, label="Photon Count (Mcps)"):
                    line_tag = f"line_series_{file_id}"
                    dpg.add_line_series(x_data, plot_data, label="Photon Count", tag=line_tag)
                
                # Apply photon plot theme
                dpg.bind_item_theme(plot_tag, self.plot_themes['photon_plot'])
                
        except Exception as e:
            print(f"Error updating photon plot: {e}")

    def _load_photon_data_to_persistent_plot(self, file_data, file_id):
        """Load photon data to the persistent plot and show controls."""
        try:
            photon_data = None
            
            # Try to get photon data from the file_data structure
            if isinstance(file_data, dict):
                if 'raw_data' in file_data and 'photon_data' in file_data['raw_data']:
                    photon_data = file_data['raw_data']['photon_data']
                elif 'photon_data' in file_data:
                    photon_data = file_data['photon_data']
            
            if photon_data is not None:
                # Process photon data for display
                photon_data = self._process_photon_data_for_display(photon_data)
                
                if photon_data is None:
                    dpg.add_text("Could not process photon data", color=[255, 100, 100])
                    return
                
                # Store current data for updates
                self.current_photon_data = photon_data
                self.current_file_id = file_id
                
                # Show the persistent plot controls and plot (statistics are now in details window)
                dpg.show_item("plot_controls_group")
                dpg.hide_item("statistics_group")  # Hide persistent statistics since we show them in details
                dpg.show_item("persistent_photon_plot")
                
                # Apply theme to the persistent plot
                dpg.bind_item_theme("persistent_photon_plot", self.plot_themes['photon_plot'])
                
                # Update the plot with initial data
                self._update_persistent_plot()
                
            else:
                # Hide plot elements if no photon data
                dpg.hide_item("plot_controls_group")
                dpg.hide_item("statistics_group")  
                dpg.hide_item("persistent_photon_plot")
                
                # Update local statistics to show no data
                if dpg.does_item_exist("local_avg_rate_text"):
                    dpg.set_value("local_avg_rate_text", "N/A")
                    dpg.set_value("local_std_rate_text", "N/A") 
                    dpg.set_value("local_min_rate_text", "N/A")
                    dpg.set_value("local_max_rate_text", "N/A")
                
                dpg.add_text("No photon data available", color=[200, 200, 200])
                
        except Exception as e:
            dpg.add_text(f"Error loading photon data: {str(e)}", color=[255, 100, 100])
            print(f"Error in loading photon data to persistent plot: {e}")

    def _update_persistent_plot(self):
        """Update the persistent plot based on current control values."""
        try:
            if self.current_photon_data is None:
                return
            
            # Get control values
            correct_for_deadtime = dpg.get_value("persistent_deadtime_checkbox")
            deadtime_ns = dpg.get_value("persistent_deadtime_input")  # Get deadtime in nanoseconds
            rebin = max(1, dpg.get_value("persistent_rebin_input"))  # Ensure minimum value of 1
            
            # Process the data
            photon_data = self.current_photon_data
            slice_arr = np.array(list(range(0, len(photon_data), rebin)) + [len(photon_data)])
            plot_data = (np.add.reduceat(photon_data, slice_arr[:-1]) / np.diff(slice_arr)).astype(np.float32)  # in Mcps
            
            if correct_for_deadtime:
                deadtime_seconds = deadtime_ns * 1e-9  # Convert nanoseconds to seconds
                plot_data = deadtime_correction(plot_data, deadtime=deadtime_seconds)
            
            x_data = np.arange(len(plot_data)) * rebin * 1e-6  # Convert to seconds
            
            # Update plot data
            dpg.set_value("persistent_line_series", [x_data.tolist(), plot_data.tolist()])
            
            # Update plot title
            dpg.configure_item("persistent_photon_plot", label=f"Photon Count vs Time (rebinned at {rebin}us)")
            
            # Update statistics
            if len(photon_data) > 0:
                avg_rate = np.mean(photon_data) * 1e3  # Convert to kcps
                std_rate = np.std(photon_data) * 1e3  # Convert to kcps
                min_rate = np.min(photon_data)
                max_rate = np.max(photon_data)
                
                # Update persistent plot statistics (in main window area)
                if dpg.does_item_exist("avg_rate_text"):
                    dpg.set_value("avg_rate_text", f"{avg_rate:.2f} kcps")
                    dpg.set_value("std_rate_text", f"{std_rate:.2f} kcps") 
                    dpg.set_value("min_rate_text", f"{min_rate:.2f} Mcps")
                    dpg.set_value("max_rate_text", f"{max_rate:.2f} Mcps")
                
                # Update local statistics (in details window)
                if dpg.does_item_exist("local_avg_rate_text"):
                    dpg.set_value("local_avg_rate_text", f"{avg_rate:.2f} kcps")
                    dpg.set_value("local_std_rate_text", f"{std_rate:.2f} kcps") 
                    dpg.set_value("local_min_rate_text", f"{min_rate:.2f} Mcps")
                    dpg.set_value("local_max_rate_text", f"{max_rate:.2f} Mcps")
                
        except Exception as e:
            print(f"Error updating persistent plot: {e}")
