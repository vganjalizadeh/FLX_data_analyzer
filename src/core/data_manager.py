import pandas as pd

class DataManager:
    def __init__(self):
        self.dataframe = None

    def load_csv(self, file_path):
        """Loads data from a CSV file."""
        try:
            self.dataframe = pd.read_csv(file_path)
            print(f"Successfully loaded {file_path}")
        except Exception as e:
            print(f"Error loading CSV: {e}")
            self.dataframe = None
        return self.dataframe

    def save_csv(self, file_path):
        """Saves data to a CSV file."""
        if self.dataframe is not None:
            try:
                self.dataframe.to_csv(file_path, index=False)
                print(f"Successfully saved to {file_path}")
            except Exception as e:
                print(f"Error saving CSV: {e}")
        else:
            print("No data to save.")

    def get_data(self):
        """Returns the current dataframe."""
        return self.dataframe

    def manipulate_data(self, operation, **kwargs):
        """Performs a data manipulation operation."""
        # Example: operation='drop_column', kwargs={'column_name': 'col1'}
        if self.dataframe is not None:
            if operation == 'drop_column':
                col = kwargs.get('column_name')
                if col in self.dataframe.columns:
                    self.dataframe.drop(columns=[col], inplace=True)
            # Add more data manipulation logic here
            return self.dataframe
        return None
