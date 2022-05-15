"""
 Summary:
    

 Author:
    Duncan Runnacles

 Created:
    7 May 2022
"""

import os

from tests import CHYME_DIR, TESTS_DIR, DATA_DIR

from chyme.tools import loaders as loaders


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
    

if __name__ == '__main__':
    load_materials()
    # load_bcdbase()
    # load_datafile_csv()