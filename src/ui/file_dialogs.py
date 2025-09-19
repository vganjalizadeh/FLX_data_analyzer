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

    def show_file_dialog(self, title="Select File", callback=None, extensions=None, multiple=False):
        """Show a file selection dialog with specified parameters."""
        try:
            root = Tk()
            root.withdraw()  # Hide the main window
            
            if extensions:
                filetypes = [(f"{ext.upper()} Files", f"*{ext}") for ext in extensions]
                filetypes.append(("All Files", "*.*"))
            else:
                filetypes = [("All Files", "*.*")]
            
            if multiple:
                files = filedialog.askopenfilenames(title=title, filetypes=filetypes)
                for file_path in files:
                    if callback:
                        callback(file_path)
            else:
                file_path = filedialog.askopenfilename(title=title, filetypes=filetypes)
                if file_path and callback:
                    callback(file_path)
                    
            root.destroy()
        except Exception as e:
            print(f"Error showing file dialog: {e}")

    def show_folder_dialog(self, title="Select Folder", callback=None):
        """Show a folder selection dialog."""
        try:
            root = Tk()
            root.withdraw()  # Hide the main window
            
            folder_path = filedialog.askdirectory(title=title)
            if folder_path and callback:
                callback(folder_path)
                
            root.destroy()
        except Exception as e:
            print(f"Error showing folder dialog: {e}")

    def show_save_dialog(self, title="Save File", callback=None, default_filename="", extensions=None):
        """Show a save file dialog."""
        try:
            root = Tk()
            root.withdraw()  # Hide the main window
            
            if extensions:
                filetypes = [(f"{ext.upper()} Files", f"*{ext}") for ext in extensions]
                filetypes.append(("All Files", "*.*"))
            else:
                filetypes = [("All Files", "*.*")]
            
            file_path = filedialog.asksaveasfilename(
                title=title, 
                initialfile=default_filename,
                filetypes=filetypes
            )
            
            if file_path and callback:
                callback(file_path)
                
            root.destroy()
        except Exception as e:
            print(f"Error showing save dialog: {e}")
