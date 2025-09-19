import numpy as np

def deadtime_correction(count_rate, deadtime=22e-9):
    """
    Apply deadtime correction to count rate data.
    Parameters:
    count_rate (array-like): Measured count rate data in Mcps.
    deadtime (float): Deadtime in seconds (default is 22 ns).
    Returns:
    array-like: Deadtime corrected count rate data.
    """
    saturation_limit = np.interp(deadtime, [22e-9, 28e-9, 62e-9], [37, 30, 12])  # in Mcps
    corrected_rate = (count_rate * 1e6) / (1 - (count_rate * 1e6 * deadtime))
    corrected_rate *= 1e-6  # Convert back to Mcps
    corrected_rate = np.clip(corrected_rate, 0, saturation_limit)
    return corrected_rate