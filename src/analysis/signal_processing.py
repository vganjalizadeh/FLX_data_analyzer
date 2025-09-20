import pathlib
import numpy as np
import pandas as pd

import pyrp
from ResultsProcessor.API.Standard import APIStandard
from ResultsProcessor.API.Native import APINative
from ResultsProcessor.Utility import FLBTools, FLRTools
from ResultsProcessor.Common import AnalysisParameters, MetaAnalysisParameters
from ResultsProcessor.SignalProcessing import SignalProcessor
from ResultsProcessor.OutlierRemoval import OutlierRemover
from ResultsProcessor.API.Dev import APIDev
from ResultsProcessor.API.NativeDev import AlgorithmModel
from ResultsProcessor.Common.SignalProcessing import IAlgorithmModel
from ResultsProcessor.Common import Matrix, Vector, AnalysisParameters, MetaAnalysisParameters

dt = 1e-6
wbeam = 6.68e-6
CHh, CHw = 6e-6, 15e-6
CHcs = CHh*CHw

metaparameters = MetaAnalysisParameters()
metaparameters.BeamWidth = wbeam
metaparameters.ChannelHeight = CHh
metaparameters.ChannelWidth = CHw
# metaparameters.CorrectionFactor = 2.34
metaparameters.CorrectionFactor = 2.00 # to match with the FPGA results

analysis_parameters = AnalysisParameters()
analysis_parameters.DetectorDeadTime = 22e-9

or_th = 5 # unit MCPS
or_bin =  1000 # unit no of bin (1e-6s)

or_parameters = MetaAnalysisParameters()
or_parameters.OutlierIntensityThreshold = or_th # unit MCPS
or_parameters.OutlierTotalSurroundingExcisedBins = or_bin # unit no of bin

meta_keys = ['AutocorrelatedVolumetricFlowRate', 'AvgBackgroundIntensity', 'AvgFLSignalIntensity', 'AvgParticleTransitTime', \
             'CompensatedAnalogIntensity', 'EffectiveRecordingTime', 'ExtendedRangeFlowRate', 'FilteredMeasurement', \
                'RecordingTime', 'SignalCV', 'SignalToBackgroundRatio', 'TotalPeakCount', 'TotalPhotonCount']
units = ['uL/min', 'kcps', 'kcps', 'us', 'kcps', 's', 'uL/min', '', 's', '%', '', '', 'kcps']

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


def analyze_photon_data(filename: str):
    data_bytes = None
    
    if filename.lower().endswith('.flb'):
        data_bytes = FLBTools.ReadFLBData(filename)
        data_bytes = data_bytes.Item2
    elif filename.lower().endswith('.flr'):
        data_bytes = FLRTools.ReadFLRData(filename)
    elif filename.lower().endswith('.flz'):
        # FLZ files contain FLR data, so we extract and read the FLR data
        import zipfile
        import tempfile
        import os
        
        try:
            with zipfile.ZipFile(filename, 'r') as zip_file:
                # Look for .flr file inside the zip
                flr_files = [f for f in zip_file.namelist() if f.lower().endswith('.flr')]
                if flr_files:
                    # Extract the first .flr file to a temporary location
                    flr_filename = flr_files[0]
                    with tempfile.TemporaryDirectory() as temp_dir:
                        extracted_path = zip_file.extract(flr_filename, temp_dir)
                        data_bytes = FLRTools.ReadFLRData(extracted_path)
                else:
                    raise ValueError("No .flr file found in the .flz archive")
        except Exception as e:
            raise ValueError(f"Error reading .flz file: {str(e)}")
    else:
        raise ValueError(f"Unsupported file format: {filename}. Only .flb, .flr, and .flz are supported.")
    
    if data_bytes is None:
        raise ValueError("Failed to read data from file")
        
    df = pd.DataFrame(columns=['FileName', 'FilePath'] + meta_keys + ['WarningFlags', 'ErrorFlags', 'ExceptionMessage'])
    
    # Add the units row (row 0) using loc instead of iloc
    df.loc[0, 'FileName'] = 'Units'
    df.loc[0, 'FilePath'] = ''
    for i, key in enumerate(meta_keys):
        df.loc[0, key] = units[i]
    # df.loc[0, 'AvgParticleTransitTime'] *= 1e6  # convert to us
    df.loc[0, 'WarningFlags'] = ''
    df.loc[0, 'ErrorFlags'] = ''
    df.loc[0, 'ExceptionMessage'] = ''
    
    n = 1

    # data_or = OutlierRemover.RemoveOutliers(data_bytes, or_parameters)
    # res = APIStandard.AnalyzeData(data_or.Item2, analysis_parameters)
    res = APIStandard.AnalyzeData(data_bytes, analysis_parameters)

    start_bins = np.array(res.StartBins)
    end_bins = np.array(res.EndBins)

    for key in meta_keys:
        df.loc[n, key] = getattr(res.MetaData, key)
    df.loc[n, 'WarningFlags'] = ', '.join([str(res.WarningFlags[i]) for i in range(len(res.WarningFlags))])
    df.loc[n, 'ErrorFlags'] = ', '.join([str(res.ErrorFlags[i]) for i in range(len(res.ErrorFlags))])
    df.loc[n, 'ExceptionMessage'] = res.ExceptionMessage
    df.loc[n, 'FileName'] = pathlib.Path(filename).name
    df.loc[n, 'FilePath'] = filename
    n += 1

    return df, start_bins, end_bins


def analyze_photon_data_raw(photon_data_array):
    """
    Analyze photon data from raw numpy array (already extracted from database).
    
    Parameters:
    photon_data_array (numpy.ndarray): Raw photon data as uint8 array
    filename (str): Optional filename for metadata
    
    Returns:
    tuple: (analysis_df, start_bins, end_bins)
    """
    # Convert numpy array to the format expected by the analysis tools
    if isinstance(photon_data_array, np.ndarray):
        # Ensure it's the right data type
        if photon_data_array.dtype != np.uint8:
            photon_data_array = photon_data_array.astype(np.uint8)
        data_bytes = photon_data_array.tobytes()
    else:
        raise ValueError("photon_data_array must be a numpy array")
    
    # Create results DataFrame
    df = pd.DataFrame(columns=meta_keys + ['WarningFlags', 'ErrorFlags', 'ExceptionMessage'])
    
    # Add the units row (row 0)
    for i, key in enumerate(meta_keys):
        df.loc[0, key] = units[i]
    # df.loc[0, 'AvgParticleTransitTime'] *= 1e6  # convert to us
    df.loc[0, 'WarningFlags'] = ''
    df.loc[0, 'ErrorFlags'] = ''
    df.loc[0, 'ExceptionMessage'] = ''
    
    n = 1

    # Run the analysis on the raw data
    data_or = OutlierRemover.RemoveOutliers(data_bytes, or_parameters)
    res = APIStandard.AnalyzeData(data_or.Item2, analysis_parameters)

    start_bins = np.array(res.StartBins)
    end_bins = np.array(res.EndBins)

    # Extract results
    for key in meta_keys:
        df.loc[n, key] = getattr(res.MetaData, key)
    df.loc[n, 'WarningFlags'] = ', '.join([str(res.WarningFlags[i]) for i in range(len(res.WarningFlags))])
    df.loc[n, 'ErrorFlags'] = ', '.join([str(res.ErrorFlags[i]) for i in range(len(res.ErrorFlags))])
    df.loc[n, 'ExceptionMessage'] = res.ExceptionMessage
    n += 1

    return df, start_bins, end_bins