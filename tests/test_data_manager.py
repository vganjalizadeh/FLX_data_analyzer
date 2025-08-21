import unittest
import pandas as pd
from src.core.data_manager import DataManager
import os

class TestDataManager(unittest.TestCase):

    def setUp(self):
        self.data_manager = DataManager()
        self.test_csv_path = "test_data.csv"
        data = {'col1': [1, 2], 'col2': [3, 4]}
        df = pd.DataFrame(data)
        df.to_csv(self.test_csv_path, index=False)

    def tearDown(self):
        os.remove(self.test_csv_path)

    def test_load_csv(self):
        df = self.data_manager.load_csv(self.test_csv_path)
        self.assertIsNotNone(df)
        self.assertEqual(df.shape, (2, 2))

if __name__ == '__main__':
    unittest.main()
