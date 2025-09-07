import dearpygui.dearpygui as dpg
import pandas as pd

class TableViewer:
    def __init__(self):
        # Create themes for row selection
        self._create_selection_themes()
        self.tag = "data_table"
        self.selected_row = None
        self.selected_row_theme = None
        self.default_row_theme = None
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
        
        # Hide placeholder text
        if dpg.does_item_exist("details_placeholder"):
            dpg.hide_item("details_placeholder")
            
        # Clear existing details content
        if dpg.does_item_exist("details_content"):
            dpg.delete_item("details_content")
        
        # Create new details content
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
                dpg.add_selectable(label=f"{row[-1]}", span_columns=True, callback=self._on_row_select, user_data=index, tag=f"row_selectable_{index}")
            dpg.bind_item_theme(f"row_{index}", self.default_row_theme)
