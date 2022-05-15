"""
 Summary:
    

 Author:
    Duncan Runnacles

 Created:
    7 May 2022
"""

import logging
import chyme
logger = logging.getLogger(__name__)

import csv
import itertools
import os

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


def load_tuflow_model(tcf_path, se_vals='', **kwargs):
    """
    """
    ext_split = os.path.splitext(tcf_path)
    if (len(ext_split) < 2 or ext_split[1] != '.tcf'):
        raise AttributeError ('TUFLOW model file must be a tcf')
    if not os.path.exists(tcf_path):
        raise AttributeError ('TUFLOW tcf file does not exist')
    
    # Load tuflow model here
    
    
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
        # # Default value, just return
        # if data == []:
        #     return [], True

        data = data.replace('"', '')
        rough_data = None
        
        # "log" values with Ks, Kappa and n-limit values
        if 'log:' in data.lower():
            # output = ['log.'] 
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
            row = {}
            # These must contain values
            try:
                row['name'] = line[header_cols['name']].strip()
                row['source'] = line[header_cols['source']].strip()
                row['column_1'] = line[header_cols['column_1']].strip()
                row['column_2'] = line[header_cols['column_2']].strip()
            except IndexError:
                logger.error('Cannot find name, source, column 1 or column 2 entries in: {}'.format(
                    os.path.split(db_path)[1]
                ))
                return None, False

            # These may contain values. Set to defaults if not
            try:
                val, success = chyme_utils.convert_str_to_int_or_float(line[header_cols['add_col_1']].strip())
                row['add_col_1'] = val if success else 0
            except IndexError:
                row['add_col_1'] = 0
            try:
                val, success = chyme_utils.convert_str_to_int_or_float(line[header_cols['mult_col_2']].strip())
                row['mult_col_1'] = val if success else 1
            except IndexError:
                row['mult_col_2'] = 1
            try:
                val, success = chyme_utils.convert_str_to_int_or_float(line[header_cols['add_col_2']].strip())
                row['add_col_2'] = val if success else 0
            except IndexError:
                row['add_col_2'] = 0
            try:
                row['column_3'] = line[header_cols['column_3']].strip()
            except IndexError:
                row['column_3'] = ''
            try:
                row['column_4'] = line[header_cols['column_4']].strip()
            except IndexError:
                row['column_4'] = ''
                
            # Process and validate the inputs
            row['name'], success = process_name(row['name'])
            row['source'], success = process_source(row['source'])
            if row['column_2'] == '' and row['source'] == '':
                logger.error('If no source entry is supplied, a constant value must be given in column 2')
                return None, False
                
            row_data.append(row)
            

    bc_dbase = data_structures.BCDbase(
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
    for line in lines:
        command, variable = tuflow_utils.split_line(line)
        data[command] = variable
        
    tpc = data_structures.TPCData(input_path, data)
    return tpc
    