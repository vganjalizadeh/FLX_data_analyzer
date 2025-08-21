import dearpygui.dearpygui as dpg

def setup_font():
    """Load and configure the Consolas font."""
    with dpg.font_registry():
        default_font = dpg.add_font("C:/Windows/Fonts/consola.ttf", 42)
    dpg.bind_font(default_font)

def setup_theme():
    """Create and apply the custom dark blue theme."""
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
            
            # Padding and spacing for better visual appeal
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 6, 6, category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 6, 6, category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_ItemInnerSpacing, 4, 4, category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 12, 12, category=dpg.mvThemeCat_Core)
            
            # Rounded corners for modern look
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 4, category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 6, category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 4, category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_PopupRounding, 4, category=dpg.mvThemeCat_Core)
    
    dpg.bind_theme(custom_theme)

def enable_dpi_awareness():
    """Enable Windows DPI awareness for crisp fonts."""
    import ctypes
    try:
        # Try PROCESS_DPI_AWARE first (value 1)
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except:
        try:
            # Fallback to older API
            ctypes.windll.user32.SetProcessDPIAware()
        except:
            pass
