import dearpygui.dearpygui as dpg

class Plugin:
    def __init__(self):
        self.name = "Example Plugin"

    def register_ui(self):
        """Registers UI elements for this plugin."""
        with dpg.menu(label=self.name, parent="primary_window"):
            dpg.add_menu_item(label="Show Info", callback=self._show_info)

    def _show_info(self):
        print(f"This is the {self.name}!")
        # In a real plugin, you might open a new window or perform an action
