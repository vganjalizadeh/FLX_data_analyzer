import dearpygui.dearpygui as dpg

class GraphViewer:
    def __init__(self):
        self.tag = "data_plot"

    def create(self, parent_container):
        """Creates the graph viewer within a given parent container."""
        with dpg.plot(label="Data Plot", height=-1, width=-1, tag=self.tag, parent=parent_container):
            dpg.add_plot_legend()
            dpg.add_plot_axis(dpg.mvXAxis, label="x-axis", tag="x_axis")
            dpg.add_plot_axis(dpg.mvYAxis, label="y-axis", tag="y_axis")

    def update_plot(self, x_data, y_data, series_label):
        """Updates the plot with new data."""
        dpg.add_line_series(x_data, y_data, label=series_label, parent="y_axis")
        dpg.fit_axis_data("x_axis")
        dpg.fit_axis_data("y_axis")
