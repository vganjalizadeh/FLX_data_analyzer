import os
import importlib

class PluginManager:
    def __init__(self, plugin_folder='plugins'):
        self.plugin_folder = plugin_folder
        self.plugins = []

    def load_plugins(self):
        """Dynamically loads plugins from the plugin folder."""
        if not os.path.exists(self.plugin_folder):
            return

        for item in os.listdir(self.plugin_folder):
            item_path = os.path.join(self.plugin_folder, item)
            if os.path.isdir(item_path):
                try:
                    module_name = f"{self.plugin_folder}.{item}.plugin"
                    plugin_module = importlib.import_module(module_name)
                    if hasattr(plugin_module, 'Plugin'):
                        plugin_instance = plugin_module.Plugin()
                        self.plugins.append(plugin_instance)
                        print(f"Loaded plugin: {plugin_instance.name}")
                        # Here you would typically register the plugin's UI elements or functions
                except Exception as e:
                    print(f"Failed to load plugin {item}: {e}")

    def get_plugins(self):
        return self.plugins
