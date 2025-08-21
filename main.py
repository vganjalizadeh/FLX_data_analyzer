import dearpygui.dearpygui as dpg
from src.core.app import App
from src.ui.theme import enable_dpi_awareness, setup_font, setup_theme

def main():
    enable_dpi_awareness()
    dpg.create_context()
    
    setup_font()
    
    app = App()
    app.setup()
    
    setup_theme()
    
    dpg.create_viewport(title='FLX Data Analyzer', width=1280, height=720)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window("primary_window", True)
    dpg.set_global_font_scale(0.5)
    dpg.start_dearpygui()
    dpg.destroy_context()

if __name__ == '__main__':
    main()
