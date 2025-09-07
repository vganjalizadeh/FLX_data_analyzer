import dearpygui.dearpygui as dpg
from tkinter import Tk, filedialog

class FileDialogs:
    def __init__(self, app):
        self.app = app
        self._create_dialogs()

    def _create_dialogs(self):
        with dpg.file_dialog(directory_selector=False, show=False, callback=self._open_callback, tag="open_file_dialog", width=700, height=400):
            dpg.add_file_extension(".flz", color=(0, 255, 0, 255))
            dpg.add_file_extension(".*")

        with dpg.file_dialog(directory_selector=False, show=False, callback=self._save_callback, tag="save_file_dialog", width=700, height=400):
            dpg.add_file_extension(".flz", color=(0, 255, 0, 255))

    def show_open_dialog(self):
        flz_files = filedialog.askopenfilenames(title="Open FLZ File", filetypes=[("FLZ Files", "*.flz"), ("All Files", "*.*")])
        for flz_file in flz_files:
            self.app.open_file(flz_file)
        # dpg.show_item("open_file_dialog")

    def show_save_dialog(self):
        dpg.show_item("save_file_dialog")

    def _open_callback(self, sender, app_data):
        if app_data and 'file_path_name' in app_data:
            self.app.open_file(app_data['file_path_name'])

    def _save_callback(self, sender, app_data):
        if app_data and 'file_path_name' in app_data:
            self.app.save_file(app_data['file_path_name'])
