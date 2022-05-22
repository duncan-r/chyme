"""
 Summary:
    

 Author:
    Duncan Runnacles

 Created:
    7 May 2022
"""

import configparser
import os

from tests import CHYME_DIR, TESTS_DIR, DATA_DIR

from chyme.tools import loaders as loaders, data_structures

    
def convert_slash(input, to_forward=True):
    original = '\\'
    after = '/'
    if not to_forward:
        after = original
        original = '/'
    output = input.replace(original, after)
    print(output)

def load_materials():
    filepath_tmf = os.path.join(DATA_DIR, 'estry_tuflow', 'model', 'Materials_TMF.tmf')
    filepath_csv = os.path.join(DATA_DIR, 'estry_tuflow', 'model', 'MaterialsCSV_AllFormats.csv')
    # tmf_file, success = loaders.load_tuflow_materials_tmf(filepath_tmf)
    # csv_file, success = loaders.load_tuflow_materials_csv(filepath_csv)
    # mat_file, success = loaders.load_tuflow_materials(filepath_tmf)
    mat_file2, success = loaders.load_tuflow_materials(filepath_csv)
    q=0
    

def load_bcdbase():
    filepath = os.path.join(DATA_DIR, 'estry_tuflow', 'bc_dbase', 'Model_1D2D.csv')
    bcdbase, success = loaders.load_tuflow_bcdbase(filepath)
    q=0
    

def load_datafile_csv():
    filepath = os.path.join(DATA_DIR, 'estry_tuflow', 'model', 'Trees.csv')
    data, success = loaders.load_tuflow_datafile_csv(filepath)
    # data, success = loaders.load_tuflow_datafile_csv(filepath, lookup_cols=[0,1])

    filepath = os.path.join(DATA_DIR, 'estry_tuflow', 'model', 'Grass.csv')
    data, success = loaders.load_tuflow_datafile_csv(filepath, lookup_names={'Grass Firm Stand <50mm': 1})

    # filepath = os.path.join(DATA_DIR, 'estry_tuflow', 'model', 'Pavement.csv')
    # data, success = loaders.load_tuflow_datafile_csv(filepath, lookup_names={'pavement d50 1.22mm': 1})
    q=0
    
def load_tpc(hartwell_folder):
    # filepath = "2d/plot/062990_EST_BAS_DES_C100_123.tpc"
    filepath = os.path.join(hartwell_folder, "2d/plot/062990_EST_BAS_DES_C100_123.tpc")
    tpc = loaders.load_tuflow_tpc(filepath)
    node_file = os.path.join(os.path.dirname(tpc.input_path), tpc.node_data_1d)
    channel_file = os.path.join(os.path.dirname(tpc.input_path), tpc.channel_data_1d)
    
    node_data = loaders.load_tuflow_results_node_csv(node_file)
    channel_data = loaders.load_tuflow_results_channel_csv(channel_file)
    q=0


def load_timeseries_csv(hartwell_folder):
    # filepath = "C:/Users/ermev/Documents/Main/Company/1_Projects/2_Open/P2112002_HighfurlongBrook_FMS/Technical/Hydraulics/Hartwell/model/Results/123/BAS/C100/2d/plot/csv/062990_EST_BAS_DES_C100_123_1d_Q.csv"
    filepath = os.path.join(hartwell_folder, "2d/plot/csv/062990_EST_BAS_DES_C100_123_1d_Q.csv")
    # filepath = "C:/Users/ermev/Documents/Main/Company/1_Projects/2_Open/P2112002_HighfurlongBrook_FMS/Technical/Hydraulics/Hartwell/model/Results/123/BAS/C100/2d/plot/csv/062990_EST_BAS_DES_C100_123_1d_H.csv"
    data = loaders.load_tuflow_timeseries_csv(filepath)
    
    time = data['time']
    flow = data['1.0001']
    q=0
    

def load_mb_csv(hartwell_folder):
    # filepath = os.path.join(hartwell_folder, "2d/062990_EST_BAS_DES_C100_123_MB.csv")
    # filepath = os.path.join(hartwell_folder, "2d/062990_EST_BAS_DES_C100_123_MB2D.csv")
    filepath = os.path.join(hartwell_folder, "1d/062990_EST_BAS_DES_C100_123_MB1D.csv")
    data = loaders.load_tuflow_mb_csv(filepath)
    
    q=0
    

def load_tuflow_results_max_csv(hartwell_folder):
    filepath = os.path.join(hartwell_folder, "2d/plot/csv/062990_EST_BAS_DES_C100_123_1d_Cmx.csv")
    # filepath = os.path.join(hartwell_folder, "2d/plot/csv/062990_EST_BAS_DES_C100_123_1d_Nmx.csv")
    
    data = loaders.load_tuflow_results_max_csv(filepath)
    
    q=0
    
    
def load_fmp_ief():
    """Load contents of an FM event (IEF) file.
    
    Would be much cleaner to use the ConfigParser class in the standard library.
    Unfortunately the ief files use a non-complient ";" character to prefix the title of
    the IED file. Generally this is used as a comment. Because the line doesn't contain
    an "=" it will fail if you turn comments off, so we have to parse this ourselves.
    
    Return:
        Ief - containing the loaded data.
    """
    ief_file = os.path.join(DATA_DIR, 'fmp', 'ief', 'Model_1.ief')
    
    lines = []
    with open(ief_file, 'r') as infile:
        lines = infile.readlines()

    ief_kwargs = {}
    ied_data = []
    snapshots = []
    for line in lines:
        line = line.strip()
        
        if line.startswith('[') and line.endswith(']'):
            continue
        elif line.startswith(';'):
            ied_data.append({'title': line.replace(';', ''), 'file': ''})
            continue
        
        command, value = line.split('=')
        command = command.lower()
        
        # Always comes after the title, so it should be safe to assume that the index exists
        if command == 'eventdata':
            ied_data[-1]['file'] = value
            
        # Same ordering and assumption here
        elif command == 'snapshottime':
            snapshots.append({'time': value, 'file': ''})
        elif command == 'snapshotfile':
            snapshots[-1]['file'] = value
        
        # Everything else is handled the same way 
        else:
            ief_kwargs[command] = value
        
    ief_kwargs['ied_data'] = ied_data
    ief_kwargs['snapshot_data'] = snapshots
    ief = data_structures.Ief(ief_file, **ief_kwargs)
    
    return ief
            

if __name__ == '__main__':
    # Hartwell results path for testing
    hartwell_folder = "C:/Users/ermev/Documents/Main/Company/1_Projects/2_Open/P2112002_HighfurlongBrook_FMS/Technical/Hydraulics/Hartwell/model/Results/123/BAS/C100/"
    
    # load_materials()
    # load_bcdbase()
    # load_datafile_csv()
    # load_timeseries_csv(hartwell_folder)
    # load_tpc(hartwell_folder)
    # load_tuflow_results_max_csv(hartwell_folder)
    # load_mb_csv(hartwell_folder)
    load_fmp_ief()