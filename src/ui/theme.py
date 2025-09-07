import dearpygui.dearpygui as dpg
import os
import platform

def setup_font():
    """Load and configure the Consolas font."""
    # Check if the os is Windows and the font path exists
    osname = platform.system()
    print(osname)
    if osname == "Windows": # Windows
        if os.path.exists("C:/Windows/Fonts/consola.ttf"):
            with dpg.font_registry():
                default_font = dpg.add_font("C:/Windows/Fonts/consola.ttf", 42)
            dpg.bind_font(default_font)
        else:
            print("Consolas font not found at C:/Windows/Fonts/consola.ttf")
    elif osname == "Darwin":  # macOS
        if os.path.exists("/System/Library/Fonts/Menlo.ttc"):
            with dpg.font_registry():
                default_font = dpg.add_font("/System/Library/Fonts/Menlo.ttc", 42)
            dpg.bind_font(default_font)
        else:
            print("Menlo font not found at /System/Library/Fonts/Menlo.ttc")
    else:
        print("Unsupported platform for custom font setup.")

def setup_theme():
    """Create and apply the custom dark blue theme."""
    with dpg.theme() as custom_theme:
        with dpg.theme_component(dpg.mvAll):
            # Background colors - almost black
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (20, 20, 25), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (25, 25, 30), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_PopupBg, (25, 25, 30), category=dpg.mvThemeCat_Core)
            
            # Frame colors - dark blue tint
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (75, 10, 55), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, (45, 50, 65), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, (55, 60, 75), category=dpg.mvThemeCat_Core)
            
            # Header colors - dark blue
            dpg.add_theme_color(dpg.mvThemeCol_MenuBarBg, (51, 51, 55), category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 8, 4, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, (70, 35, 70), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, (80, 45, 80), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_Header, (75, 10, 55), category=dpg.mvThemeCat_Core)
            
            # Table row hover and selection styles - FIX HEIGHT ISSUES
            dpg.add_theme_style(dpg.mvStyleVar_CellPadding, 4, 0, category=dpg.mvThemeCat_Core)  # Proper cell padding
            dpg.add_theme_style(dpg.mvStyleVar_SelectableTextAlign, 0.0, 0.0, category=dpg.mvThemeCat_Core)  # Center align vertically
            
            # Title bar colors for docked windows
            dpg.add_theme_color(dpg.mvThemeCol_TitleBg, (40, 0, 5), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, (60, 0, 5), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgCollapsed, (35, 5, 0), category=dpg.mvThemeCat_Core)
            
            # COMPREHENSIVE tab and docking colors - FORCE override all blues
            dpg.add_theme_color(dpg.mvThemeCol_Tab, (75, 10, 55), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_TabHovered, (95, 15, 65), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_TabActive, (115, 20, 75), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_TabUnfocused, (55, 8, 40), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_TabUnfocusedActive, (75, 10, 55), category=dpg.mvThemeCat_Core)
            
            # TAB BAR SPECIFIC COLORS - this should fix the blue tab bar!
            try:
                # These might be the specific tab bar colors
                dpg.add_theme_color(dpg.mvThemeCol_MenuBarBg, (30, 30, 35), category=dpg.mvThemeCat_Core)  # Tab bar background
                dpg.add_theme_color(dpg.mvThemeCol_ScrollbarBg, (30, 30, 35), category=dpg.mvThemeCat_Core)  # Sometimes used for tab bars
                dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrab, (75, 10, 55), category=dpg.mvThemeCat_Core)
                dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabHovered, (95, 15, 65), category=dpg.mvThemeCat_Core)
                dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabActive, (115, 20, 75), category=dpg.mvThemeCat_Core)
            except:
                pass
            
            # Override EVERY possible blue highlight/selection color
            dpg.add_theme_color(dpg.mvThemeCol_NavHighlight, (115, 20, 75), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_NavWindowingHighlight, (115, 20, 75), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_NavWindowingDimBg, (30, 30, 35), category=dpg.mvThemeCat_Core)
            
            # Force override docking and separator colors
            dpg.add_theme_color(dpg.mvThemeCol_DockingPreview, (115, 20, 75), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_DockingEmptyBg, (30, 30, 35), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_Separator, (75, 10, 55), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_SeparatorHovered, (95, 15, 65), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_SeparatorActive, (115, 20, 75), category=dpg.mvThemeCat_Core)
            
            # Override ALL resize and grip colors
            dpg.add_theme_color(dpg.mvThemeCol_ResizeGrip, (75, 10, 55), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ResizeGripHovered, (95, 15, 65), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ResizeGripActive, (115, 20, 75), category=dpg.mvThemeCat_Core)
            
            # Override any selection/highlight colors that might cause blue
            # dpg.add_theme_color(dpg.mvThemeCol_TextSelectedBg, (95, 15, 65), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrab, (95, 15, 65), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrabActive, (115, 20, 75), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_CheckMark, (115, 20, 75), category=dpg.mvThemeCat_Core)
            
            # Override plot colors
            dpg.add_theme_color(dpg.mvThemeCol_PlotLines, (95, 15, 65), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_PlotLinesHovered, (115, 20, 75), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_PlotHistogram, (95, 15, 65), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_PlotHistogramHovered, (115, 20, 75), category=dpg.mvThemeCat_Core)
            
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
            # dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 4, category=dpg.mvThemeCat_Core)
            # dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 6, category=dpg.mvThemeCat_Core)
            # dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 4, category=dpg.mvThemeCat_Core)
            # dpg.add_theme_style(dpg.mvStyleVar_PopupRounding, 4, category=dpg.mvThemeCat_Core)
            # dpg.add_theme_style(dpg.mvStyleVar_TabRounding, 6, category=dpg.mvThemeCat_Core)
            
            # TAB BAR HEIGHT - try to minimize or eliminate the blue tab bar
            try:
                dpg.add_theme_style(dpg.mvStyleVar_TabBarBorderSize, 0, category=dpg.mvThemeCat_Core)
                dpg.add_theme_style(dpg.mvStyleVar_TabBorderSize, 0, category=dpg.mvThemeCat_Core)
            except:
                pass
    
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
