import pandas as pd

def calculate_mean(dataframe, column_name):
    """Calculates the mean of a column."""
    if dataframe is not None and column_name in dataframe.columns:
        return dataframe[column_name].mean()
    return None

def calculate_std_dev(dataframe, column_name):
    """Calculates the standard deviation of a column."""
    if dataframe is not None and column_name in dataframe.columns:
        return dataframe[column_name].std()
    return None
