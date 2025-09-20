import dearpygui.dearpygui as dpg
import pandas as pd
import numpy as np
import threading
import concurrent.futures
from .theme import create_plot_themes
from ..analysis.signal_processing import deadtime_correction, analyze_photon_data, analyze_photon_data_raw

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
        
        # Threading for background processing
        self.thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        self.processing_lock = threading.Lock()
        self.current_processing_task = None
        
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
        print(f"load_database_records called with {len(records_df) if records_df is not None else 0} records")
        if records_df is None or records_df.empty:
            # Show empty table with appropriate columns (replace File ID with Row)
            empty_df = pd.DataFrame(columns=["Row", "File Name", "File Type", "Peak Count", "Avg Background", "Transit Time"])
            self.data = empty_df
            self.update_data(empty_df)
            return
        
        # Store original data for row selection details (keep File ID and File Path for operations)
        self.database_records = records_df
        
        # Create display version with row numbers instead of File ID (hide File Path for cleaner display)
        display_df = records_df.copy()
        columns_to_hide = ['File ID', 'File Path']
        # Remove columns that exist in the dataframe
        columns_to_hide = [col for col in columns_to_hide if col in display_df.columns]
        display_df = display_df.drop(columns=columns_to_hide)
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
                    dpg.add_spacer(height=2)
                    
                    # Display basic file information in a more compact format
                    for col_name, value in record.items():
                        with dpg.group(horizontal=True):
                            dpg.add_text(f"{col_name}:", color=[200, 200, 200])
                            dpg.add_spacer(width=10)
                            dpg.add_text(f"{value}", color=[255, 255, 100], wrap=300)  # Yellow color for values, wrap long text
                
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
        
        # Load existing analysis results for this record
        if file_id and self.app:
            self._load_existing_analysis_results(file_id)

    def _add_detailed_file_analysis(self, file_id):
        """Add detailed file analysis including plots, statistics, and images."""
        # Show loading indicator in the details content area
        loading_text = dpg.add_text("Loading detailed data...", color=[200, 200, 100], parent="details_content")
        
        # Load data in background thread
        future = self.thread_pool.submit(self._load_file_data, file_id)
        future.add_done_callback(lambda f: self._on_file_data_loaded(f, file_id, loading_text))
    
    def _load_file_data(self, file_id):
        """Load file data from database in background thread."""
        try:
            file_data = self.app.get_file_data(file_id)
            return file_data
        except Exception as e:
            print(f"Error loading file data: {e}")
            return None
    
    def _on_file_data_loaded(self, future, file_id, loading_text):
        """Callback when file data loading completes."""
        try:
            file_data = future.result()
            
            # Remove loading text
            if dpg.does_item_exist(loading_text):
                dpg.delete_item(loading_text)
            
            if not file_data:
                dpg.add_text("No detailed data available", color=[255, 100, 100], parent="details_content")
                return
            
            # Update persistent plot with new data (this will show statistics and plot controls above)
            self._load_photon_data_to_persistent_plot(file_data, file_id)
            
            # Add images below the persistent plot (they will appear in the details content area) 
            self._add_image_display(file_data, file_id)
            
        except Exception as e:
            if dpg.does_item_exist(loading_text):
                dpg.delete_item(loading_text)
            dpg.add_text(f"Error loading detailed data: {str(e)}", color=[255, 100, 100], parent="details_content")
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
            dpg.add_spacer(height=10, parent="details_content")
            dpg.add_text("Images:", color=[200, 200, 100], parent="details_content")
            
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
            with dpg.group(horizontal=True, parent="details_content"):
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
            dpg.add_text(f"Error displaying images: {str(e)}", color=[255, 100, 100], parent="details_content")
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
                        try:
                            dpg.add_text("Not available", color=[200, 200, 200])
                        except:
                            print("Image not available")
                        return
                except:
                    try:
                        dpg.add_text("Could not parse image data", color=[255, 100, 100])
                    except:
                        print("Could not parse image data")
                    return
            
            if image_data is None:
                try:
                    dpg.add_text("Not available", color=[200, 200, 200])
                except:
                    print("Image not available")
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
                        try:
                            dpg.add_text("Invalid image dimensions", color=[255, 100, 100])
                        except:
                            print("Invalid image dimensions")
                        return
                
                # Get image dimensions
                if len(image_data.shape) == 2:
                    height, width = image_data.shape
                    channels = 1
                elif len(image_data.shape) == 3:
                    height, width, channels = image_data.shape
                else:
                    try:
                        dpg.add_text("Unsupported image format", color=[255, 100, 100])
                    except:
                        print("Unsupported image format")
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
                        try:
                            dpg.add_text(f"Unsupported channel count: {channels}", color=[255, 100, 100])
                        except:
                            print(f"Unsupported channel count: {channels}")
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
                try:
                    dpg.add_text("No image data", color=[200, 200, 200])
                except:
                    print("No image data")
                
        except Exception as e:
            try:
                dpg.add_text(f"Error displaying image: {str(e)}", color=[255, 100, 100])
            except:
                print(f"Error displaying image: {str(e)}")
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
        if not self.app:
            print("No app reference available")
            return
        
        # Load data in background thread
        future = self.thread_pool.submit(self._load_file_data, file_id)
        future.add_done_callback(lambda f: self._on_view_file_data_loaded(f, file_id))
    
    def _on_view_file_data_loaded(self, future, file_id):
        """Callback when file data loading completes for viewing."""
        try:
            file_data = future.result()
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
            # dpg.add_separator()
            
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
            
            # dpg.add_separator()
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
                # Show status message
                print(f"Deleting record: {file_id}...")
                
                # Perform delete in background thread
                future = self.thread_pool.submit(self.app.delete_file, file_id)
                future.add_done_callback(lambda f: self._on_delete_complete(f, file_id))
            
            # Close confirmation dialog
            dpg.delete_item("delete_confirmation_dialog")
            
        except Exception as e:
            print(f"Error confirming delete: {e}")
    
    def _on_delete_complete(self, future, file_id):
        """Callback when delete operation completes."""
        try:
            success = future.result()
            if success:
                print(f"Successfully deleted record: {file_id}")
                # Refresh the table
                self._refresh_table_data()
            else:
                print(f"Failed to delete record: {file_id}")
        except Exception as e:
            print(f"Error in delete completion callback: {e}")

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
                    # Show status message
                    print(f"Duplicating record: {file_id}...")
                    
                    # Perform duplication in background thread
                    future = self.thread_pool.submit(self.app.duplicate_file, file_id)
                    future.add_done_callback(lambda f: self._on_duplicate_complete(f, file_id))
                else:
                    print("Duplicate functionality not available")
        except Exception as e:
            print(f"Error duplicating record: {e}")
    
    def _on_duplicate_complete(self, future, original_file_id):
        """Callback when duplicate operation completes."""
        try:
            new_file_id = future.result()
            if new_file_id:
                print(f"Successfully duplicated record: {original_file_id} -> {new_file_id}")
                # Refresh the table
                self._refresh_table_data()
            else:
                print(f"Failed to duplicate record: {original_file_id}")
        except Exception as e:
            print(f"Error in duplicate completion callback: {e}")

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
                # Show status message
                print(f"Renaming file: {file_id} -> {new_name}...")
                
                # Perform rename in background thread
                future = self.thread_pool.submit(self.app.rename_file, file_id, new_name.strip())
                future.add_done_callback(lambda f: self._on_rename_complete(f, file_id, new_name))
            else:
                print("Rename functionality not available")
            
            # Close rename dialog
            dpg.delete_item("rename_dialog")
            
        except Exception as e:
            print(f"Error confirming rename: {e}")
    
    def _on_rename_complete(self, future, file_id, new_name):
        """Callback when rename operation completes."""
        try:
            success = future.result()
            if success:
                print(f"Successfully renamed file: {file_id} -> {new_name}")
                # Refresh the table
                self._refresh_table_data()
            else:
                print(f"Failed to rename file: {file_id}")
        except Exception as e:
            print(f"Error in rename completion callback: {e}")

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
        print("_refresh_table_data called")
        if self.app and hasattr(self.app, 'data_manager'):
            import dearpygui.dearpygui as dpg
            
            def do_refresh():
                try:
                    # Get fresh data from database
                    files_data = self.app.data_manager.list_files()
                    print(f"Retrieved {len(files_data) if files_data is not None else 0} records from database")
                    
                    if files_data is not None and isinstance(files_data, pd.DataFrame):
                        self.load_database_records(files_data)
                        print(f"Table refreshed with {len(files_data)} database records after analysis")
                    else:
                        print("No database records found during refresh")
                except Exception as e:
                    print(f"Error refreshing table data: {e}")
            
            # Force this to run in the main thread
            if dpg.is_dearpygui_running():
                # Schedule for next frame if GUI is running
                dpg.set_frame_callback(1, callback=do_refresh)
            else:
                # If GUI not running, execute directly
                do_refresh()
    
    def _on_table_refresh_complete(self, future):
        """Callback when table refresh completes."""
        try:
            updated_records = future.result()
            self.load_database_records(updated_records)
        except Exception as e:
            print(f"Error refreshing table data: {e}")

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
                # Show loading indicator for processing
                processing_text = dpg.add_text("Processing photon data...", color=[200, 200, 100], parent="details_content")
                
                # Process photon data in background thread
                future = self.thread_pool.submit(self._process_photon_data_for_display, photon_data)
                future.add_done_callback(lambda f: self._on_photon_data_processed(f, file_id, processing_text))
                
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
                
                dpg.add_text("No photon data available", color=[200, 200, 200], parent="details_content")
                
        except Exception as e:
            dpg.add_text(f"Error loading photon data: {str(e)}", color=[255, 100, 100], parent="details_content")
            print(f"Error in loading photon data to persistent plot: {e}")
    
    def _on_photon_data_processed(self, future, file_id, processing_text):
        """Callback when photon data processing completes."""
        try:
            # Remove processing text
            if dpg.does_item_exist(processing_text):
                dpg.delete_item(processing_text)
            
            photon_data = future.result()
            
            if photon_data is None:
                dpg.add_text("Could not process photon data", color=[255, 100, 100], parent="details_content")
                return
            
            # Store current data for updates
            self.current_photon_data = photon_data
            self.current_file_id = file_id
            
            # Show the persistent plot controls and plot (statistics are now in details window)
            dpg.show_item("plot_controls_group")
            dpg.hide_item("statistics_group")  # Hide persistent statistics since we show them in details
            dpg.show_item("persistent_photon_plot")
            
            # Apply theme to the persistent plot
            # dpg.bind_item_theme("persistent_photon_plot", self.plot_themes['photon_plot'])
            
            # Update the plot with initial data
            self._update_persistent_plot()
            
        except Exception as e:
            if dpg.does_item_exist(processing_text):
                dpg.delete_item(processing_text)
            dpg.add_text(f"Error processing photon data: {str(e)}", color=[255, 100, 100], parent="details_content")
            print(f"Error in photon data processing callback: {e}")

    def _update_persistent_plot(self):
        """Update the persistent plot based on current control values."""
        if self.current_photon_data is None:
            return
        
        # Cancel any existing processing task
        with self.processing_lock:
            if self.current_processing_task and not self.current_processing_task.done():
                self.current_processing_task.cancel()
        
        # Get control values
        correct_for_deadtime = dpg.get_value("persistent_deadtime_checkbox")
        deadtime_ns = dpg.get_value("persistent_deadtime_input")  # Get deadtime in nanoseconds
        rebin = max(1, dpg.get_value("persistent_rebin_input"))  # Ensure minimum value of 1
        
        # Submit processing to background thread
        future = self.thread_pool.submit(self._process_plot_data, 
                                       self.current_photon_data.copy(), 
                                       correct_for_deadtime, deadtime_ns, rebin)
        
        with self.processing_lock:
            self.current_processing_task = future
        
        # Set callback for when processing completes
        future.add_done_callback(self._on_plot_processing_complete)
    
    def _process_plot_data(self, photon_data, correct_for_deadtime, deadtime_ns, rebin):
        """Process plot data in background thread."""
        try:
            # Process the data
            slice_arr = np.array(list(range(0, len(photon_data), rebin)) + [len(photon_data)])
            plot_data = (np.add.reduceat(photon_data, slice_arr[:-1]) / np.diff(slice_arr)).astype(np.float32)  # in Mcps
            
            if correct_for_deadtime:
                deadtime_seconds = deadtime_ns * 1e-9  # Convert nanoseconds to seconds
                plot_data = deadtime_correction(plot_data, deadtime=deadtime_seconds)
            
            x_data = np.arange(len(plot_data)) * rebin * 1e-6  # Convert to seconds
            
            # Calculate statistics
            statistics = {}
            if len(photon_data) > 0:
                statistics = {
                    'avg_rate': np.mean(photon_data) * 1e3,  # Convert to kcps
                    'std_rate': np.std(photon_data) * 1e3,   # Convert to kcps
                    'min_rate': np.min(photon_data),
                    'max_rate': np.max(photon_data)
                }
            
            return {
                'x_data': x_data.tolist(),
                'plot_data': plot_data.tolist(),
                'rebin': rebin,
                'statistics': statistics
            }
            
        except Exception as e:
            print(f"Error processing plot data: {e}")
            return None
    
    def _on_plot_processing_complete(self, future):
        """Callback when background plot processing completes."""
        try:
            result = future.result()
            if result is None:
                return
            
            # Update UI on main thread
            dpg.set_value("persistent_line_series", [result['x_data'], result['plot_data']])
            dpg.configure_item("persistent_photon_plot", label=f"Photon Count vs Time (rebinned at {result['rebin']}us)")
            
            # Update statistics
            stats = result['statistics']
            if stats:
                # Update persistent plot statistics (in main window area)
                if dpg.does_item_exist("avg_rate_text"):
                    dpg.set_value("avg_rate_text", f"{stats['avg_rate']:.2f} kcps")
                    dpg.set_value("std_rate_text", f"{stats['std_rate']:.2f} kcps") 
                    dpg.set_value("min_rate_text", f"{stats['min_rate']:.2f} Mcps")
                    dpg.set_value("max_rate_text", f"{stats['max_rate']:.2f} Mcps")
                
                # Update local statistics (in details window)
                if dpg.does_item_exist("local_avg_rate_text"):
                    dpg.set_value("local_avg_rate_text", f"{stats['avg_rate']:.2f} kcps")
                    dpg.set_value("local_std_rate_text", f"{stats['std_rate']:.2f} kcps") 
                    dpg.set_value("local_min_rate_text", f"{stats['min_rate']:.2f} Mcps")
                    dpg.set_value("local_max_rate_text", f"{stats['max_rate']:.2f} Mcps")
                
        except Exception as e:
            print(f"Error updating UI after plot processing: {e}")
        finally:
            # Clear the current task
            with self.processing_lock:
                if self.current_processing_task == future:
                    self.current_processing_task = None
    
    def _analyze_current_photon_data(self):
        """Analyze the currently loaded photon data using signal processing."""
        if self.current_photon_data is None or self.current_file_id is None:
            print("No photon data available for analysis")
            return
        
        # Show progress indicators
        dpg.show_item("analysis_progress_group")
        dpg.set_value("analysis_status_text", "Preparing analysis...")
        dpg.set_value("analysis_progress_bar", 0.1)
        dpg.configure_item("analyze_photon_button", enabled=False)
        
        # Get the current file record for filename metadata
        
        print("Starting analysis of photon data")
        # Start background analysis using the raw photon data
        future = self.thread_pool.submit(self._run_photon_analysis_raw, 
                                       self.current_photon_data.copy())
        future.add_done_callback(self._on_analysis_complete)
    
    def _run_photon_analysis_raw(self, photon_data):
        """Run the photon data analysis using raw data in background thread."""
        try:
            # Update progress
            self._update_analysis_progress(0.2, "Processing photon data...")
            
            self._update_analysis_progress(0.4, "Running signal analysis...")
            
            # Call the analysis function with raw photon data
            analysis_df, start_bins, end_bins = analyze_photon_data_raw(photon_data)
            
            self._update_analysis_progress(0.8, "Processing results...")
            
            # Extract the analysis results (skip the header row with units)
            if len(analysis_df) > 1:
                results_row = analysis_df.iloc[1]  # Row 1 contains the actual results
                
                # Create analysis results dictionary using proper pandas indexing
                analysis_results = {
                    'analysis_complete': True,
                    'total_peak_count': results_row['TotalPeakCount'] if 'TotalPeakCount' in results_row.index else 0,
                    'flowrate': results_row['AutocorrelatedVolumetricFlowRate'] if 'AutocorrelatedVolumetricFlowRate' in results_row.index else 0,
                    'avg_background': results_row['AvgBackgroundIntensity'] if 'AvgBackgroundIntensity' in results_row.index else 0,
                    'avg_fl_signal': results_row['AvgFLSignalIntensity'] if 'AvgFLSignalIntensity' in results_row.index else 0,
                    'avg_particle_transit_time': results_row['AvgParticleTransitTime'] if 'AvgParticleTransitTime' in results_row.index else 0,
                    'signal_cv': results_row['SignalCV'] if 'SignalCV' in results_row.index else 0,
                    'signal_to_bg_ratio': results_row['SignalToBackgroundRatio'] if 'SignalToBackgroundRatio' in results_row.index else 0,
                    'recording_time': results_row['RecordingTime'] if 'RecordingTime' in results_row.index else 0,
                    'effective_recording_time': results_row['EffectiveRecordingTime'] if 'EffectiveRecordingTime' in results_row.index else 0,
                    'total_photon_count': results_row['TotalPhotonCount'] if 'TotalPhotonCount' in results_row.index else 0,
                    'start_bins': start_bins.tolist() if start_bins is not None else [],
                    'end_bins': end_bins.tolist() if end_bins is not None else [],
                    'warning_flags': results_row['WarningFlags'] if 'WarningFlags' in results_row.index else '',
                    'error_flags': results_row['ErrorFlags'] if 'ErrorFlags' in results_row.index else '',
                    'exception_message': results_row['ExceptionMessage'] if 'ExceptionMessage' in results_row.index else ''
                }
                
                self._update_analysis_progress(1.0, "Analysis complete!")
                return analysis_results
            else:
                raise Exception("No analysis results returned")
                
        except Exception as e:
            print(f"Error in photon analysis: {e}")
            return {'error': str(e)}
    
    def _run_photon_analysis(self, file_path):
        """Run the photon data analysis in background thread."""
        try:
            # Update progress
            self._update_analysis_progress(0.2, "Loading file data...")
            
            # Call the analysis function from signal_processing
            analysis_df, start_bins, end_bins = analyze_photon_data(file_path)
            
            self._update_analysis_progress(0.8, "Processing results...")
            
            # Extract the analysis results (skip the header row with units)
            if len(analysis_df) > 1:
                results_row = analysis_df.iloc[1]  # Row 1 contains the actual results
                
                # Create analysis results dictionary using proper pandas indexing
                analysis_results = {
                    'analysis_complete': True,
                    'total_peak_count': results_row['TotalPeakCount'] if 'TotalPeakCount' in results_row.index else 0,
                    'flowrate': results_row['AutocorrelatedVolumetricFlowRate'] if 'AutocorrelatedVolumetricFlowRate' in results_row.index else 0,
                    'avg_background': results_row['AvgBackgroundIntensity'] if 'AvgBackgroundIntensity' in results_row.index else 0,
                    'avg_fl_signal': results_row['AvgFLSignalIntensity'] if 'AvgFLSignalIntensity' in results_row.index else 0,
                    'avg_particle_transit_time': results_row['AvgParticleTransitTime'] if 'AvgParticleTransitTime' in results_row.index else 0,
                    'signal_cv': results_row['SignalCV'] if 'SignalCV' in results_row.index else 0,
                    'signal_to_bg_ratio': results_row['SignalToBackgroundRatio'] if 'SignalToBackgroundRatio' in results_row.index else 0,
                    'recording_time': results_row['RecordingTime'] if 'RecordingTime' in results_row.index else 0,
                    'total_photon_count': results_row['TotalPhotonCount'] if 'TotalPhotonCount' in results_row.index else 0,
                    'start_bins': start_bins.tolist() if start_bins is not None else [],
                    'end_bins': end_bins.tolist() if end_bins is not None else [],
                    'warning_flags': results_row['WarningFlags'] if 'WarningFlags' in results_row.index else '',
                    'error_flags': results_row['ErrorFlags'] if 'ErrorFlags' in results_row.index else '',
                    'exception_message': results_row['ExceptionMessage'] if 'ExceptionMessage' in results_row.index else ''
                }
                
                self._update_analysis_progress(1.0, "Analysis complete!")
                return analysis_results
            else:
                raise Exception("No analysis results returned")
                
        except Exception as e:
            print(f"Error in photon analysis: {e}")
            return {'error': str(e)}
    
    def _update_analysis_progress(self, progress, status_text):
        """Update progress bar and status text (thread-safe)."""
        try:
            if dpg.does_item_exist("analysis_progress_bar"):
                dpg.set_value("analysis_progress_bar", progress)
            if dpg.does_item_exist("analysis_status_text"):
                dpg.set_value("analysis_status_text", status_text)
        except:
            pass  # Ignore UI update errors in background thread
    
    def _on_analysis_complete(self, future):
        """Callback when analysis completes."""
        print("_on_analysis_complete called")
        try:
            result = future.result()
            
            if 'error' in result:
                self._show_analysis_error(f"Analysis failed: {result['error']}")
                return
            
            # Save results to database
            if self.app and hasattr(self.app, 'update_file_analysis'):
                success = self.app.update_file_analysis(self.current_file_id, result)
                if success:
                    print(f"Analysis results saved for file: {self.current_file_id}")
                    
                    # Update the plot with peak indicators
                    self._add_peak_indicators_to_plot(result.get('start_bins', []), 
                                                     result.get('end_bins', []))
                    
                    # Show success message
                    dpg.set_value("analysis_status_text", 
                                f"Analysis complete! Found {result.get('total_peak_count', 0)} peaks")
                    
                    # Refresh table to show updated data - schedule in main thread
                    print("Scheduling table refresh after analysis completion")
                    import dearpygui.dearpygui as dpg
                    
                    # Try a direct call first to see if it works
                    try:
                        self._refresh_table_data()
                        print("Direct table refresh completed")
                    except Exception as e:
                        print(f"Direct refresh failed: {e}")
                        # Fallback to frame callback
                        dpg.set_frame_callback(1, callback=self._refresh_table_data)
                else:
                    self._show_analysis_error("Failed to save analysis results to database")
            else:
                self._show_analysis_error("Database update method not available")
                
        except Exception as e:
            self._show_analysis_error(f"Error processing analysis results: {str(e)}")
        finally:
            # Hide progress bar and re-enable button after 3 seconds
            def hide_progress():
                dpg.hide_item("analysis_progress_group")
                dpg.configure_item("analyze_photon_button", enabled=True)
            
            # Use a simple timer approach
            import time
            import threading
            timer = threading.Timer(3.0, hide_progress)
            timer.start()
    
    def _show_analysis_error(self, error_message):
        """Show analysis error and reset UI."""
        print(f"Analysis error: {error_message}")
        dpg.set_value("analysis_status_text", f"Error: {error_message}")
        dpg.set_value("analysis_progress_bar", 0.0)
        dpg.configure_item("analyze_photon_button", enabled=True)
        
        # Hide progress after 5 seconds
        def hide_progress():
            dpg.hide_item("analysis_progress_group")
        
        import threading
        timer = threading.Timer(5.0, hide_progress)
        timer.start()
    
    def _add_peak_indicators_to_plot(self, start_bins, end_bins):
        """Update persistent scatter plot series with peak start/end markers at y=0."""
        try:
            if not start_bins or not end_bins:
                # Clear scatter series if no peaks
                if dpg.does_item_exist("peak_starts_scatter"):
                    dpg.set_value("peak_starts_scatter", [[], []])
                if dpg.does_item_exist("peak_ends_scatter"):
                    dpg.set_value("peak_ends_scatter", [[], []])
                return
            
            # Convert bin indices to time values (assuming 1μs per bin)
            rebin = max(1, dpg.get_value("persistent_rebin_input"))
            start_times = np.array(start_bins) * 1e-6  # Convert to seconds
            end_times = np.array(end_bins) * 1e-6      # Convert to seconds
            
            # Check if scatter series exist
            if not dpg.does_item_exist("peak_starts_scatter") or not dpg.does_item_exist("peak_ends_scatter"):
                print("Peak scatter series not found")
                return
            
            # Create markers at y=0 for all peaks
            # Use all zeros for y coordinates to place markers at the bottom
            start_y_values = np.zeros_like(start_times)
            end_y_values = np.zeros_like(end_times)
            
            # Update the persistent scatter series with new data
            dpg.set_value("peak_starts_scatter", [start_times.tolist(), start_y_values.tolist()])
            dpg.set_value("peak_ends_scatter", [end_times.tolist(), end_y_values.tolist()])
            
            print(f"Updated scatter markers: {len(start_bins)} peak starts, {len(end_bins)} peak ends")
            
        except Exception as e:
            print(f"Error updating peak indicators: {e}")
    
    def _clear_peak_indicators(self):
        """Clear all existing peak indicators from the plot."""
        try:
            # Clear the persistent scatter series
            if dpg.does_item_exist("peak_starts_scatter"):
                dpg.set_value("peak_starts_scatter", [[], []])
            if dpg.does_item_exist("peak_ends_scatter"):
                dpg.set_value("peak_ends_scatter", [[], []])
        except Exception as e:
            print(f"Error clearing peak indicators: {e}")
    
    def _load_existing_analysis_results(self, file_id):
        """Load existing analysis results for a file and update peak indicators."""
        try:
            if not self.app or not hasattr(self.app, 'data_manager'):
                return
            
            # Get file data from database
            file_data = self.app.get_file_data(file_id)
            if not file_data:
                return
            
            # Check if analysis results exist
            if isinstance(file_data, dict) and 'photon_analysis' in file_data:
                analysis_data = file_data['photon_analysis']
                
                if 'results' in analysis_data:
                    # Parse results JSON
                    import json
                    try:
                        if isinstance(analysis_data['results'], str):
                            results = json.loads(analysis_data['results'])
                        else:
                            results = analysis_data['results']
                        
                        # Extract start and end bins
                        start_bins = results.get('start_bins', [])
                        end_bins = results.get('end_bins', [])
                        
                        if start_bins and end_bins:
                            print(f"Loading {len(start_bins)} peaks from existing analysis")
                            # Update peak indicators on the plot
                            self._add_peak_indicators_to_plot(start_bins, end_bins)
                            
                    except json.JSONDecodeError as e:
                        print(f"Error parsing analysis results: {e}")
            else:
                print("No existing analysis results found")        
                        
        except Exception as e:
            self._clear_peak_indicators()
            print(f"Error loading existing analysis results: {e}")
    
    def cleanup(self):
        """Clean up resources, especially the thread pool."""
        try:
            # Cancel any pending tasks
            with self.processing_lock:
                if self.current_processing_task and not self.current_processing_task.done():
                    self.current_processing_task.cancel()
            
            # Shutdown the thread pool
            self.thread_pool.shutdown(wait=True, timeout=5.0)
            print("Thread pool successfully shut down")
        except Exception as e:
            print(f"Error during cleanup: {e}")
