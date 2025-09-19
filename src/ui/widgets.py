import dearpygui.dearpygui as dpg

class StatusBar:
    def __init__(self):
        self.tag = "status_bar_text"

    def create(self, parent):
        with dpg.group(horizontal=True, parent=parent):
            dpg.add_text("Ready", tag=self.tag)

    def set_text(self, text):
        dpg.set_value(self.tag, text)

    def set_status(self, status):
        """Set the status text (alias for set_text for compatibility)."""
        self.set_text(status)

class ProgressBar:
    def __init__(self):
        self.tag = "progress_bar"

    def create(self, parent):
        dpg.add_progress_bar(tag=self.tag, width=200, overlay="Progress", parent=parent, show=True)

    def show(self):
        dpg.show_item(self.tag)

    def hide(self):
        dpg.hide_item(self.tag)

    def set_progress(self, value):
        """Sets the progress value (0.0 to 1.0)."""
        dpg.set_value(self.tag, value)
