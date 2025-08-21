import dearpygui.dearpygui as dpg

class TableViewer:
    def __init__(self):
        self.tag = "data_table"

    def create(self, parent_container):
        """Creates the table within a given parent container."""
        with dpg.table(tag=self.tag, header_row=True, resizable=True, policy=dpg.mvTable_SizingStretchProp,
                       row_background=True, borders_innerV=True, borders_outerV=True, delay_search=True,
                       sortable=True, parent=parent_container):
            pass # Columns and data will be added dynamically

    def update_data(self, dataframe):
        if dataframe is None:
            return

        # Clear existing table content
        dpg.delete_item(self.tag, children_only=True)

        # Add new columns
        for col in dataframe.columns:
            dpg.add_table_column(label=col, parent=self.tag)

        # Add new rows
        for index, row in dataframe.iterrows():
            with dpg.table_row(parent=self.tag):
                for item in row:
                    dpg.add_text(str(item))
