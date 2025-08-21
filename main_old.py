import dearpygui.dearpygui as dpg
from src.core.app import App
import ctypes

def main():
    # Enable DPI awareness for Windows
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # PROCESS_DPI_AWARE
    except:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except:
            pass
    
    dpg.create_context()
    
    # Load Consolas font with higher DPI scaling
    with dpg.font_registry():
        default_font = dpg.add_font("C:/Windows/Fonts/consola.ttf", 42)
    
    # Create custom dark blue theme
    with dpg.theme() as custom_theme:
        with dpg.theme_component(dpg.mvAll):
            # Background colors - almost black
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (20, 20, 25), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (25, 25, 30), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_PopupBg, (25, 25, 30), category=dpg.mvThemeCat_Core)
            
            # Frame colors - dark blue tint
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (35, 40, 55), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, (45, 50, 65), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, (55, 60, 75), category=dpg.mvThemeCat_Core)
            
            # Header colors - dark blue
            dpg.add_theme_color(dpg.mvThemeCol_Header, (40, 45, 60), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, (50, 55, 70), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, (60, 65, 80), category=dpg.mvThemeCat_Core)
            
            # Button colors - dark blue
            dpg.add_theme_color(dpg.mvThemeCol_Button, (40, 45, 60), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (50, 55, 70), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (60, 65, 80), category=dpg.mvThemeCat_Core)
            
            # Text colors
            dpg.add_theme_color(dpg.mvThemeCol_Text, (220, 220, 220), category=dpg.mvThemeCat_Core)
            
            # Border colors - subtle blue
            dpg.add_theme_color(dpg.mvThemeCol_Border, (60, 65, 80), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_BorderShadow, (10, 10, 15), category=dpg.mvThemeCat_Core)
    
    app = App()
    app.setup()
    
    # Bind the font to all items
    dpg.bind_font(default_font)
    
    # Apply the custom theme
    dpg.bind_theme(custom_theme)
    
    dpg.set_primary_window("primary_window", True)

    dpg.create_viewport(title='FLX Data Analyzer', width=1280, height=720)
    dpg.setup_dearpygui()
    
    # Set global font scale to 0.5 for crisp rendering
    dpg.set_global_font_scale(0.5)
    
    dpg.show_viewport()
    dpg.set_primary_window("primary_window", True)
    dpg.start_dearpygui()
    dpg.destroy_context()

if __name__ == '__main__':
    main()
