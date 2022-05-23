"""
 Summary:
    

 Author:
    Duncan Runnacles

 Created:
    7 May 2022
"""

import logging
import chyme
from chyme.tools.data_structures import TuflowResultsNodeMaxEntry
logger = logging.getLogger(__name__)

import csv
import itertools
import numpy
import os
import re

from chyme.utils import logsettings as logset
from chyme.tuflow import loader as tuflow_loader
from chyme.tuflow import tuflow_utils
from chyme.utils import utils as chyme_utils
from chyme.tools import data_structures as ds, data_structures


class LoadListener(logset.ChymeProgressListener):
    
    def progress(self, progress, **kwargs): 
        pass
    
    def notify(self, message, **kwargs):
        print('Load listener msg: '.format(message))


class ModelLoader():
    """Interface for all Chyme loaders.
    
    Provides a standard interface thatat loader should implement. Includes
    setup and shutdown returns and implements a message update system.
    """
    
    def __init__(self, filepath, **kwargs):
        self.input_path = filepath
        self.kwargs = kwargs
        self._message_listener = LoadListener()
        self.model = None
        
    def load(self):
        self.setup()
        self.load()
        self.shutdown()
    
    def setup(self):
        logset.add_progress_listener(self._message_listener)
        
    def load_model(self):
        raise NotImplementedError
        
    def shutdown(self):
        logset.remove_progress_listener(self._message_listener)
    
    def load_messages(self):
        return self._message_listener.get_logs()
    
    
class TuflowModelLoader(ModelLoader):
    """TODO: This should be in the TUFLOW package."""
    
    def load_model(self):
        se_vals = self.kwargs.pop('se_vals', '')
        loader = tuflow_loader.TuflowLoader(self.input_path, se_vals=se_vals, **self.kwargs)
        loader.load()
        self.model = loader
    

def load_model(filepath, **kwargs):
    name_ext = os.path.splitext(filepath)
    if len(name_ext) < 2:
        raise ValueError('Path does not contain a file extention: '.format(filepath))
    
    if name_ext[1] == '.tcf' or name_ext[1] == '.ecf':
        loader = load_tuflow_model(filepath, **kwargs)
        return loader


def load_tuflow_model(tcf_path, **kwargs):
    """
    """
    ext_split = os.path.splitext(tcf_path)
    if (len(ext_split) < 2 or ext_split[1] != '.tcf'):
        raise AttributeError ('TUFLOW model file must be a tcf')
    if not os.path.exists(tcf_path):
        raise AttributeError ('TUFLOW tcf file does not exist')
    
    # Load tuflow model here
    loader = TuflowModelLoader(tcf_path, **kwargs)
    loader.load_model()
    return loader
    
    
def load_tuflow_materials(mat_path, **kwargs):
    ext_split = os.path.splitext(mat_path)
    if len(ext_split) < 2 or ext_split[1] not in ['.csv', '.tmf']:
        raise AttributeError ('mat_path must be a TUFLOW csv or tmf materials file')
    
    if ext_split == 'tmf':
        mat, success = load_tuflow_materials_tmf(mat_path, **kwargs)
    else:
        mat, success = load_tuflow_materials_csv(mat_path, **kwargs)
    return mat, success
        

def load_tuflow_materials_tmf(mat_path, **kwargs):
    """Load the contents of a TUFLOW materials 'tmf' format file.

    """
    
    lines = []
    try:
        with open(mat_path, 'r') as infile:
            lines = infile.readlines()
    except OSError as e:
        logger.warning('Unable to read materials file: {}'.format(mat_path))
        return None, False
        
    header_cols = [
        'material_id', 'n_value', 'init_loss', 'cont_loss', 'y1', 'n1', 'y2', 'n2',
        'reserved', 'srf', 'fract_imperv'
    ]
    default_values = [
        None, None, 0, 0, -1, -1, -1, -1, -1, 0, 0
    ]
    header_cols_as_read = []
    row_data = []
    for i, line in enumerate(lines):
        strip_line = line.strip()
        strip_line = strip_line.replace('#', '!')
        if strip_line.startswith('!'):
            continue
        if strip_line == '':
            continue
        
        strip_line, comment = tuflow_utils.remove_comment(strip_line, return_comment=True)
        split_line = chyme_utils.remove_multiple_whitespace(strip_line)
        split_line = [val.strip() for val in strip_line.split(',')]
        if not header_cols_as_read:
            header_cols_as_read = split_line
        else:
            if len(split_line) < 2:
                logger.warning('Materials files must contain at least an ID and N value (cols 1 and 2)')
                return None, False

            if len(split_line) < 12:
                split_line += ['0'] * (len(default_values) - len(split_line))
            # row_data.append(
            #     dict(itertools.zip_longest(header_cols, split_line, fillvalue=None))
            # )
            # row_data[-1]['comment'] = comment
            fixed_row = dict(itertools.zip_longest(header_cols, split_line, fillvalue=None))
            n_data = None
            if fixed_row[4:8] == [-1, -1, -1, -1]:
                if fixed_row[1] is None:
                    logger.warning('Materials file must contain at N values')
                    return None, False
                n_data = data_structures.TuflowMaterialsMannings(
                    fixed_row[1], data_structures.TuflowMaterialsMannings.SINGLE_N
                )
            else:
                n_data = data_structures.TuflowMaterialsMannings(
                    fixed_row[4:8], data_structures.TuflowMaterialsMannings.DEPTH_VARYING_N
                )
                
            row_data.append(data_structures.TuflowMaterialsEntry(
                fixed_row[0], n_data, rainfall_losses=[fixed_row[2], fixed_row[3]],
                hazard_id=fixed_row[8], srf=fixed_row[9], fract_imperv=fixed_row[10]
            ))
    # mat = ds.TuflowMaterials(
    #     mat_path, row_data, header_cols, headers_as_read=header_cols_as_read
    # )
    mat = ds.TuflowMaterials(
        mat_path, row_data, header_cols, headers_as_read=header_cols_as_read
    )
    return mat, True
        

def load_tuflow_materials_csv(mat_path, **kwargs):
    """Load the contents of a TUFLOW materials 'csv' format file.
    
    """
    
    def process_n_col(data):

        data = data.replace('"', '')
        rough_data = None
        
        # "log" values with Ks, Kappa and n-limit values
        if 'log:' in data.lower():
            data = data[4:]
            # Can be comma or space delimited
            # Seriously, really - come on man, just pick one!
            if ',' in data:
                data = data.split(',')
            else:
                data = data.split()
            try:
                temp = [float(d) for d in data]
                rough_data = data_structures.TuflowMaterialsLogLaw(
                    temp[0], temp[1], temp[2]
                )
            except ValueError:
                logger.warning('Materials unknown log value format in column 2')
                return None, False
        
        else:
            use_VxD = False
            n_type = -1
            n_data = []

            # Try treating as n values
            n_vals = data.split(',')
            
            # Check whether we have the vxd keywork
            if data.lower().startswith('vxd:'):
                use_VxD = True
                data = data[4:]

            # Single 'n' value
            if len(n_vals) < 2 and not 'csv' in n_vals[0]:
                n_type = data_structures.TuflowMaterialsMannings.SINGLE_N
                try:
                    temp = float(data)
                    rough_data = data_structures.TuflowMaterialsMannings(
                        temp, n_type, use_VxD=use_VxD
                    )
                except ValueError:
                    logger.warning("Materials unknown n value format in column 2")
                    return None, False

            # Two sets of depth / 'n' values (n1, y1, n2, y2)
            elif len(n_vals) == 4:
                n_type = data_structures.TuflowMaterialsMannings.DEPTH_VARYING_N
                try:
                    temp = [
                        [float(n_vals[0]), float(n_vals[1])],
                        [float(n_vals[2]), float(n_vals[3])],
                    ]
                    rough_data = data_structures.TuflowMaterialsMannings(
                        temp, n_type, use_VxD=use_VxD
                    )
                except ValueError:
                    logger.warning("Materials unknown multiple n value format in column 2")
                    return None, False
                    
            # Includes a filename (and possible pipe separated column names)
            # Pipes as separator this time I guess! (┛ಠ_ಠ)┛彡┻━┻
            else:
                n_type = data_structures.TuflowMaterialsMannings.DEPTH_VARYING_N
                fpath = name1 = name2 = None
                if '|' in data:
                    data = data.split('|')
                    fpath = data[0].strip()
                    name1 = data[1].strip() if len(data) > 1 else None
                    name2 = data[2].strip() if len(data) > 2 else None
                else:
                    fpath = data.strip()

                try:
                    nonlocal mat_path
                    mat_dir = os.path.dirname(mat_path)
                    subpath = os.path.join(mat_dir, fpath)
                    lookup_names = {}
                    n_data = []
                    
                    # Names are given for both lookup columns (depth must be first, then 'n')
                    if name2 is not None:
                        lookup_names = {name1: 0, name2: 0}
                        values, success = load_tuflow_datafile_csv(subpath, lookup_names=lookup_names)
                        if success:
                            n_data = []
                            for i in range(0, len(values[name1.lower()])):
                                n_data.append([values[name1.lower()][i], values[name2.lower()][i]])
                    
                    # Names given for first column only (find the second to the right of it)
                    elif name1 is not None:
                        lookup_names = {name1: 1}
                        values, success = load_tuflow_datafile_csv(subpath, lookup_names=lookup_names)
                        if success:
                            n_data = []
                            for i in range(0, len(values[name1.lower()])):
                                n_data.append([values[name1.lower()][i], values['{}_{}'.format(name1.lower(), 0)][i]])
                                      
                    # No names given, assume first two columns
                    else:
                        values, success = load_tuflow_datafile_csv(subpath)
                        if success:
                            n_data = []
                            for i in range(0, len(values[0])):
                                n_data.append([values[0][i], values[1][i]])
                    
                    if not n_data:
                        logger.error('Failed to find some lookup names in file: '.format(lookup_names))
                        return None, False
                    
                    rough_data = data_structures.TuflowMaterialsMannings(
                        n_data, n_type, filepath=subpath, use_VxD=use_VxD
                    )
 
                except OSError:
                    logger.error('Could not open depth varying roughness file: {}'.format(subpath))
                    return None, False
            
        return rough_data, True
        
    def process_loss_col(data):
        data = data.replace('"', '')
        data = data.split(',')
        if len(data) < 2:
            logger.warning('Materials rainfall loss values format issue in column 3, setting to [0,0]')
            return ['0','0'], False
        try:
            v1 = float(data[0])
            v2 = float(data[1])
            return [v1, v2], True
        except ValueError:
            logger.warning('Materials rainfall loss values format issue in column 3, setting to [0,0]')
            return ['0','0'], False
    
    def process_hazard_col(data):
        if data.strip() == '': return -1, True
        try:
            return int(data), True
        except ValueError:
            logger.warning('Materials hazard ID format issue in column 4, setting to ""')
            return "", True

    def process_srf_col(data):
        try:
            srf_val = float(data)
            return srf_val, True
        except ValueError:
            logger.warning('Materials srf value format issue in column 5, setting to 0')
            return '0', False
    
    def process_imperv_col(data):
        fi = '0.0'
        try:
            fi = float(data)
            if fi < 0:
                fi = '0.0'
                logger.warning('Materials fraction impervious is < 0, setting to 0.0')
            elif fi > 1:
                fi = '1.0'
                logger.warning('Materials fraction impervious is > 1, setting to 1.0')
        except ValueError:
            logger.warning('Materials fraction impervious value format issue in column 6')
        return fi, False

    lines = []
    try:
        with open(mat_path, 'r') as infile:
            input = csv.reader(infile, delimiter=',')
            for i in input:
                lines.append(i)
    except OSError as e:
        logger.warning('Unable to read materials file: {}'.format(mat_path))
        return None, False
        
    header_cols = [
        'material_id', 'n_value', 'rain_loss', 'hazard_id', 'srf', 'fract_imperv', 'comment'
    ]
    default_values = [None, None, [0,0], -1, 0, 0.0]
    header_cols_as_read = []
    row_data = []
    param_fail = False
    found_headers = False
    for i, line in enumerate(lines):

        # Pull the comment out
        comment = ''
        line[-1].replace('#', '!')
        if '!' in line[-1]:
            comment = line[-1].replace('!', '').strip()
            line = line[:-1]

        if not found_headers:
            if line[0].strip() == '':
                continue
            else:
                found_headers = True
                header_cols_as_read = line
        else:
            if len(line) < 2:
                logger.warning('Materials files must contain at least an ID and N value (cols 1 and 2)')
                return None, False

            if len(line) < 6:
                line += [default_values[i] for i in range(len(line), len(default_values))]
                
            mat_id = line[0]
            n_data, success = process_n_col(line[1])

            # Must have roughness values (can't default), so we raise an error here
            # TODO: I mean, we could default? I expect we don't want to though?
            if not success:
                logger.error('Cannot parse required roughness values in {}'.format(
                    os.path.split(mat_path)[1]
                ))
                return None, False

            # All others could have null values. Defaults will be used if unfound or there's issues
            loss_data, success = process_loss_col(line[2])
            hazard_id, success = process_hazard_col(line[3])
            srf, success = process_srf_col(line[4])
            fract_imperv, success = process_imperv_col(line[5])
            
            row_data.append(data_structures.TuflowMaterialsEntry(
                mat_id, n_data, rainfall_losses=loss_data, hazard_id=hazard_id,
                srf=srf, fract_imperv=fract_imperv, comment=comment
            ))
            
            
    if param_fail:
        logger.warning('Parsing issues on some values (see output above) for: {}'.format(
            os.path.split(mat_path)[1])
        )
    
    mat = ds.TuflowMaterials(
        mat_path, row_data, header_cols, headers_as_read=header_cols_as_read
    )
    return mat, True
    
    
def load_tuflow_bcdbase(db_path):
    """Load the contents of a TUFLOW bc_dbase csv file.

    """
    
    def process_name(data):
        
        # References a lookup in a .ts1 file
        # Note: 'RAFTS' in not currently supported
        if '|' in data:
            split_data = data.split('|')
            group = data[1].strip()
            id = data[0].strip()
            return [id, group], True
        
        # Otherwise it should be a lookup id for the 1d_bc/2d_bc layer 'name'
        else:
            return [data.strip()], True
        
    def process_source(data):
        """
        
        Note::
            RAFTS, XP, WBNM_Meta, FEWS, and possibly other files not currently supported.
            Currently supports csv, ts1 and constant values.
        """
        
        data = data.strip()
        
        # Blank entry means a constant value applied in 'column_2'
        if data == '' or '.csv' in data or '.ts1' in data:
            return data, True
        else:
            logger.error('source parsing error or format not support for: {}'.format(data))
            return data, False
        

    
    lines = []
    try:
        with open(db_path, 'r') as infile:
            input = csv.reader(infile, delimiter=',')
            for i in input:
                lines.append(i)
    except OSError as e:
        logger.warning('Unable to read materials file: {}'.format(db_path))
        return None, False
        
    header_cols = {
        'name': 0, 'source': 1, 'column_1': 2, 'column_2': 3, 'add_col_1': 4, 
        'mult_col_2': 5, 'add_col_2': 6,  'column_3': 7, 'column_4': 8, 
    }
    # Lookup names for different ids that column headers are allowed
    header_col_lookup = {
        'column 1': 'column_1', 'time': 'column_1', 'column 2': 'column_2', 
        'value': 'column_2', 'id': 'column_2', 'add col 1': 'add_col_1', 
        'timeadd': 'add_col_1', 'mult col 2': 'mult_col_2', 'valuemult': 'mult_col_2', 
        'add col 2': 'add_col_2', 'valueadd': 'add_col_2', 'column 3': 'column_3', 
        'column 4': 'column_4',
    }
    header_col_lookup_keys = header_col_lookup.keys()

    header_cols_as_read = []
    row_data = []
    found_headers = False
    for i, line in enumerate(lines):
        if not found_headers:
            if line[0].strip() == '':
                continue
            else:
                found_headers = True
                header_cols_as_read = line
                # Work out how the input columns are ordered
                # Only do values after name and source, because they must be in the
                # first two columns. The others can be ordered or referenced by name
                for i in range(2, len(line)):
                    low_line = line[i].lower()
                    if low_line in header_col_lookup_keys:
                        header_cols[header_col_lookup[low_line]] = i
        else:
            # Setup defaults
            add_col_1 = 0
            add_col_2 = 0
            mult_col_2 = 1
            column_1 = ''
            column_2 = ''
            column_3 = ''
            column_4 = ''
            # These must contain values
            try:
                name = line[header_cols['name']].strip()
                source = line[header_cols['source']].strip()
                column_1 = line[header_cols['column_1']].strip()
                column_2 = line[header_cols['column_2']].strip()
            except IndexError:
                logger.error('Cannot find name, source, column 1 or column 2 entries in: {}'.format(
                    os.path.split(db_path)[1]
                ))
                return None, False

            # These may contain values. Set to defaults if not
            try:
                val, success = chyme_utils.convert_str_to_int_or_float(line[header_cols['add_col_1']].strip())
                if success: add_col_1 = val
            except IndexError:
                pass
            try:
                val, success = chyme_utils.convert_str_to_int_or_float(line[header_cols['mult_col_2']].strip())
                if success: mult_col_2 = val
            except IndexError:
                pass
            try:
                val, success = chyme_utils.convert_str_to_int_or_float(line[header_cols['add_col_2']].strip())
                if success: add_col_2 = val
            except IndexError:
                pass
            try:
                column_3 = line[header_cols['column_3']].strip()
            except IndexError:
                pass
            try:
                column_4 = line[header_cols['column_4']].strip()
            except IndexError:
                pass
                
            # Process and validate the inputs
            name, success_name = process_name(name)
            source, success_source = process_source(source)
            if not success_name or not success_source:
                logger.error('Failed to pass name or source input for: '.format(db_path))

            if column_2 == '' and source == '':
                logger.error('If no source entry is supplied, a constant value must be given in column 2')
                return None, False
            
            row_data.append(data_structures.TuflowBCDbaseEntry(
                name, source, parent_path=db_path, column_1=column_1, column_2=column_2, 
                add_col_1=add_col_1, mult_col_2=mult_col_2, add_col_2=add_col_2,
                column_3=column_3, column_4=column_4
            ))

    bc_dbase = data_structures.TuflowBCDbase(
        db_path, row_data, list(header_cols.keys()), header_cols_as_read=header_cols_as_read
    ) 
    return bc_dbase, True
    
    
def load_tuflow_datafile_csv(input_path, **kwargs):
    """
    
    Args:
        input_path (str): the filepath to load the csv data from.
    
    kwargs:
        lookup_cols (list): list of column indices to return the data from.
        lookup_names (dict): dict of column header names to return the data from. The
            value of the name should be the number of adjacent columns to return.
        skip_non_numeric_rows=True (bool): skip rows after the headers if they contain
            non-numeric values.
            
    For the lookup_names, the dict provides the column name to find and a number denoting
    have many adjacent columns of data to return. For example, to return only the data in
    the column containing the name use::

        {'colname': 0}
        
    to return three adjacent columns of data, including the column containing the name and 
    the next two columns to the right use::
    
        {'colname': 2}
        
    This approach can be applied to multiple names, for example::
    
        {'colname': 1, 'colname2': 2, 'colname3': 0, 'colname4': 1, ...}
    
    Note that, if no lookup_cols or lookup_names kwargs are supplied, the default will be
    to return data from all columns in the file. If both lookup_cols and lookup_names
    are supplied the lookup_names will be used. All rows before the provided lookup names
    will be skipped.
    
    Return:
        dict - if all data or column data requested the keys will be the column number
        
    For lookup_cols and lookup_names a dict is used to provide a reference to the column
    data returned (e.g. return_data[1] for cols or return_data[colname] for names). As
    adjacent column data can be requested, an additional key entry will be created for 
    each adjacent column with the number appended to the column id string, for example::
    
        # By name
        return_data, success = load_tuflow_data_csv(input_path, lookup_names={'mycol': 2})
        print(return_data)
        >>> return data = {
                'mycol':     [0.1, 0.5, 1.2],
                'mycol_0':   [3, 0.7, 2.3],
                'mycol_1':   [2.2, 1, 1.7],
                ...
            }
        
        # By column index
        return_data, success = load_tuflow_data_csv(input_path, lookup_cols={3: 2})
        print(return_data)
        >>> return data = {
                3:     [0.1, 0.5, 1.2],
                '3_0': [3, 0.7, 2.3],
                '3_1': [2.2, 1, 1.7],
                ...
            }
        
    """
    LOOKUP_ALL = 0
    LOOKUP_COLS = 1
    LOOKUP_NAMES = 2

    if not os.path.exists(input_path):
        raise OSError('Input path does not exist at: {}'.format(input_path))
    
    ext_split = os.path.splitext(input_path)
    if len(ext_split) < 2 or ext_split[1] != '.csv':
        raise AttributeError('Input path must be a csv file')
    
    # kwargs
    skip_nonnumeric_rows = kwargs.get('skip_nonnumeric_rows', True)
    lookup_cols = kwargs.get('lookup_cols', [])
    lookup_names = kwargs.get('lookup_names', {})

    lookup_names = {name.lower(): col_count for name, col_count in lookup_names.items()}
    lookup_type = LOOKUP_ALL
    lookup_refs = {}
    
    # Setup lookup dict
    if lookup_names: 
        lookup_type = LOOKUP_NAMES
        lookup_refs = dict.fromkeys(lookup_names.keys(), -1)
    elif lookup_cols:
        lookup_type = LOOKUP_COLS
        lookup_refs = dict.fromkeys(lookup_cols, lookup_cols)
    
    lines = {}
    col_only_lines = {}
    found_headers = False
    header_cols_as_read = []
    
    try:
        with open(input_path, 'r') as infile:
            csv_data = csv.reader(infile, delimiter=',')
            for i, input in enumerate(csv_data):
                
                # Handle the header row stuff
                if not found_headers:

                    # Skip initial blank lines
                    if not any(temp.strip() for temp in input):
                        continue

                    # Only get the values from the specific column names
                    # NOTE: Assumes that all column headers are in the same row, not staggered
                    if lookup_type == LOOKUP_NAMES:
                        
                        # Check the names exist and fail if not
                        for j, header in enumerate(input):
                            low_header = header.lower().strip()
                            if low_header in lookup_names:
                                lookup_refs[low_header] = j
                                col_only_lines[low_header] = []
                                
                                # Create additional names for adjacent columns
                                # In the format "lookupname_number" (e.g. "depth_1")
                                for k in range(0, lookup_names[low_header]):
                                    col_only_lines['{}_{}'.format(low_header, k)] = []
                                header_cols_as_read.append(low_header)

                        # Name couldn't be found (default column index (-1)) so we don't 
                        # know what data to grab
                        if -1 in lookup_refs.values():
                            logger.error('Some lookup names could not be found in headers')
                            return None, False
                        found_headers = True

                    else:
                        # Only get the values from the specific columns
                        if lookup_type == LOOKUP_COLS:
                            short_line = []
                            for ref in lookup_refs:
                                short_line.append(input[ref])
                                col_only_lines[ref] = []
                                
                                # Create additional names for adjacent columns
                                # In the format "lookupname_number" (e.g. "depth_1")
                                for k in range(0, lookup_names[ref]):
                                    col_only_lines['{}_{}'.format(low_header, k)] = []
                                header_cols_as_read.append(low_header)

                            header_cols_as_read = short_line
                            
                        # Get the values from all columns
                        else:
                            header_cols_as_read = input
                            for col, val in enumerate(input):
                                lines[col] = []
                        found_headers = True

                    
                
                # Handle the data row stuff
                else:
                    # Only fetch specific columns
                    if lookup_type == LOOKUP_COLS or lookup_type == LOOKUP_NAMES:
                        for ref_name, ref_count in lookup_refs.items():
                            short_line = []

                            # Check the row first to make sure it has numeric values
                            val, success = chyme_utils.convert_str_to_int_or_float(input[ref_count])
                            if skip_nonnumeric_rows and not success:
                                break
                            
                            # Then handle fetching the values for all columns requested
                            # (i.e. named column plus number of adjacent)
                            else:
                                # Add the main column value
                                col_only_lines[ref_name].append(val)
                                if lookup_type == LOOKUP_NAMES:
                                    
                                    # For each adjacent value, use the main column name + "_N"
                                    # to find the lookup (matches header setup for output cols)
                                    if lookup_names[ref_name] > 0:
                                        
                                        # ref_count == position of main column
                                        # k == position to the right of the main column
                                        # (0-indexed, so move across one column (k+1))
                                        for k in range(0, lookup_names[ref_name]):
                                            val, success = chyme_utils.convert_str_to_int_or_float(
                                                input[ref_count + k + 1]
                                            )
                                            col_only_lines['{}_{}'.format(ref_name, k)].append(val)

                    # We're fetching the data from all of the columns
                    else:
                        # Skip rows if they don't contain numeric data
                        if skip_nonnumeric_rows:
                            val, success = chyme_utils.convert_str_to_int_or_float(input[0])
                            if not success: 
                                continue
                        for col, val in enumerate(input):
                            lines[col].append(val)

    except OSError as e:
        logger.error('Unable to read datafile: {}'.format(input_path))
        return None, False
    
    print(header_cols_as_read)
    
    if lines:
        return lines, True
    else:
        return col_only_lines, True
    
    
def load_tuflow_tpc(input_path, **kwargs):
    """Load the contents of a TUFLOW .tpc file.
    
    Contains references to the location of the data needed to read the results of the a
    TUFLOW simulation. 
    
    Create a new TPCData object to store the data in.
    
    Args:
        input_path (str): the file path of the .tpc file.
        
    Return:
        TPCData instance containing the loaded data.
        
    Raises:
        OSError: if the input_path file does not exist.
        AttributeError: if the input_path is not a TUFLOW .tpc file.
    """
    
    if not os.path.exists(input_path):
        raise OSError('Input .tpc filepath does not exist: {}'.format(input_path))

    ext_split = os.path.splitext(input_path)
    if len(ext_split) < 2 or ext_split[1] != '.tpc':
        raise AttributeError('Input path must be a TUFLOW tpc file')
    
    lines = []
    with open(input_path, 'r') as infile:
        lines = infile.readlines()
    
    data = {}
    bracket_match = re.compile('\[\d+\]')
    for line in lines:
        command, variable = tuflow_utils.split_line(line)
        
        # Some tpc command contain bracketed numbers (e.g. "[18]") after the command
        # string
        if re.search(bracket_match, command):
            cmd_split = command.split('[')
            command = cmd_split[0].strip().lower()
            cmd_count = cmd_split[1].replace('[', '').replace(']', '').strip()
            variable = (variable, cmd_count)
        data[command.lower()] = variable
        
    tpc = data_structures.TPCData(input_path, data)
    return tpc


def load_tuflow_timeseries_csv(input_path, column_names=None, no_data_val=-99999, use_sensible_names=True):
    """Load TUFLOW timeseries results.
    
    Will check for a 'time' column by string compare and all data will be converted to 
    Float32 format. If expected characters (from TUFLOW) are find in the column names and
    the use_sensible_names value is True, the column names will be stripped of all 
    unnecessary additional data and only the node ID kept.

    These can be any file in the format of something like::
    
        row num    |    time    |    data1    |    data2    |    ...
        1          |    0       |    0        |    0        |    ...
        2          |    0.5     |    1.2      |    0.6      |    ...
        3          |    0.7     |    1.3      |    0.9      |    ...
        ...
        
    Return:
        numpy.ndarray - containing Float32 data.
    """
    
    headers = []
    start_row = 0
    with open(input_path, 'r') as infile:
        line = infile.readline().strip()
        while line == '':
            start_row += 1
            line = infile.readline().strip()

        headers = line.split(',')
        
    use_cols = None
    if column_names:
        use_cols = [i for i, name in enumerate(headers) if name in column_names]
    
    sens_name_lookup = ['Q', 'H', 'V', 'D', 'SQ']
    sensible_names = []
    if use_sensible_names:
        for i, name in enumerate(headers):
            name = name.replace('"', '')
            # temp = name[:2]
            if 'time' in name.lower():
                sensible_names.append('time')
            elif name[:2].strip() in sens_name_lookup:
                split_name = name.split()
                sensible_names.append(split_name[1])
            else:
                sensible_names.append(name)
        
    data = numpy.genfromtxt(
        input_path, delimiter=',', dtype=numpy.float32, skip_header=start_row, 
        filling_values=no_data_val, names=True, usecols=use_cols
    )
    data.dtype.names = tuple(sensible_names)
    q=0
    return data


def load_tuflow_mb_csv(input_path):
    """Load TUFLOW mass balance (_MB, _MB1D and _MB2D) results.
        
    Return:
        numpy.ndarray - containing Float32 data.
    """
    mb_cols = []
    if '_MB1D.csv' in input_path:
        mb_cols = [
            'time', '1d_dom', 'hv_in', 'hv_out', 'qv_in', 'qv_out', 'qrv_in', 'qrv_out', 'x1dh_v_in', 
            'x1dh_v_out', 'x1dq_v_in', 'x1dq_v_out', 'sx2d_v_in', 'sx2d_v_out', 'hx2d_v_in', 
            'hx2d_v_out', 'q2d_v_in', 'q2d_v_out', 'vol_io', 'dvol', 'vol_error', 'p_qme',
            'total_vol', 'cum_vol_io', 'cum_vol_error', 'p_cum_me', 'p_cum_qme'
        ]
        
    elif '_MB2D.csv' in input_path:
        mb_cols = [
            'time', '1d_dom', 'hv_in', 'hv_out', 'eshx_v_in', 'eshx_v_out', 'x1dhx_v_in', 
            'x1dhx_v_out', 'ss_v_in', 'ss_v_out', 'essx_v_in', 'essx_v_out', 'x1dsx_v_in', 
            'x1dsx_v_out', 'vol_io', 'dvol', 'vol_error', 'p_qme', 'total_vol',
            'cum_v_io', 'cum_v_error', 'p_cum_me', 'p_cum_qme'
        ]
        
    elif '_MB.csv' in input_path:
        mb_cols = [
            'time', '1D_2D', 'h_vol_in', 'h_vol_out', 'q_vol_in', 'q_vol_out', 'total_vol_in',
            'total_vol_out', 'vol_io_minus', 'dvol', 'vol_error', 'p_qme', 'vol_io_plus',
            'total_vol', 'cum_vol_io', 'cum_vol_err', 'p_cum_me', 'p_cum_qme', 
        ]
    else:
        raise ValueError('Unrecognised file format for TUFLOW MB csv file')
    
    
    data = numpy.genfromtxt(
        input_path, delimiter=',', dtype=numpy.float32, filling_values=0,
        names=True
    )
    data.dtype.names = tuple(mb_cols)
    return data


def load_tuflow_results_node_csv(input_path):
    """Load the contents of the TUFLOW 1d_Node csv file."""
    
    lines = []
    with open(input_path, 'r') as infile:
        lines = infile.readlines()
    lines = lines[1:]

    rows = {}
    for l in lines:
        line = l.split(',')
        data = {}
        data['row_id']          = int(line[0])
        data['node']            = line[1].replace('"', '').strip()
        data['bed_level']       = float(line[2])
        data['top_level']       = float(line[3])
        data['num_channels']    = int(line[4])
        data['channels']        = [chan.strip() for chan in line[5:]]
        rows[data['node']] = data_structures.TuflowResultsNodeDataEntry(data)
        
    node_data = data_structures.TuflowResultsNodeData(input_path, rows)
    return node_data


def load_tuflow_results_channel_csv(input_path):
    """Load the contents of the TUFLOW 1d_Chan csv file."""
    
    lines = []
    with open(input_path, 'r') as infile:
        lines = infile.readlines()
    lines = lines[1:]

    rows = {}
    for l in lines:
        line = l.split(',')
        data = {}
        data['row_id']          = int(line[0])
        data['channel']         = line[1].replace('"', '').strip()
        data['us_node']         = line[2].replace('"', '').strip()
        data['ds_node']         = line[3].replace('"', '').strip()

        us_channel = line[4].replace('"', '').strip()
        ds_channel = line[5].replace('"', '').strip()
        data['us_channel'] = '' if us_channel == '------' else us_channel
        data['ds_channel'] = '' if ds_channel == '------' else ds_channel

        data['flags']           = line[6].replace('"', '').strip()
        data['length']          = float(line[7])
        data['form_loss']       = float(line[8])
        data['n_or_cd']         = float(line[9])
        data['p_slope']         = float(line[10])
        data['us_invert']       = float(line[11])
        data['ds_invert']       = float(line[12])
        data['lb_us_obvert']    = float(line[13])
        data['rb_us_obvert']    = float(line[14])
        data['lb_ds_obvert']    = float(line[15])
        data['rb_ds_obvert']    = float(line[16])
        data['p_blockage']      = float(line[17])
        rows[data['channel']] = data_structures.TuflowResultsChannelDataEntry(data)
        
    node_data = data_structures.TuflowResultsChannelData(input_path, rows)
    return node_data


def load_tuflow_results_max_csv(input_path):
    """Load TUFLOW max results (Cmx and Nmx) type files."""
    
    lines = []
    with open(input_path, 'r') as infile:
        lines = infile.readlines()
    
    entries = {}
    headers = []
    split_row = lines[0].split(',')
    # Grab every other column starting at column 2
    # Results are in the format: rowid, name, res1, res1 time, res2, res2 time, ...
    for i in range(2, len(split_row), 2):
        if len(split_row) > i + 1:
            headers.append(split_row[i])

    lines = lines[1:]
    for l in lines:
        line = l.split(',')
        row_id = line[0]
        result_id = line[1]
        temp_data = {}
        hcount = 0
        for i in range(2, len(line), 2):
            temp_data[headers[hcount]] = {
                'max': float(line[i].strip()), 'time': float(line[i+1].strip())
            }
            hcount += 1
        
        entries[result_id] = TuflowResultsNodeMaxEntry({
            'row_id': row_id, 'id': result_id, 'max_data': temp_data
        })
        
    max_data = data_structures.TuflowResultsNodeData(input_path, entries)
    return max_data


def load_fmp_ief(ief_file):
    """Load contents of an FM event (IEF) file.
    
    Would be much cleaner to use the ConfigParser class in the standard library.
    Unfortunately the ief files use a non-complient ";" character to prefix the title of
    the IED file. Generally this is used as a comment. Because the line doesn't contain
    an "=" it will fail if you turn comments off, so we have to parse this ourselves.
    
    Return:
        Ief - containing the loaded data.
    """
    
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
        