"""
 Summary:
    

 Author:
    Duncan Runnacles

 Created:
    7 May 2022
"""
import logging
logger = logging.getLogger(__name__)

import os


class TuflowMaterialsMannings():
    SINGLE_N        = 0
    DEPTH_VARYING_N = 1
    
    def __init__(self, n_data, n_type, filepath=None, use_VxD=False):
        """Setup roughness values.
        
        TUFLOW allows for a lot of variation in providing roughness values, but they all
        come down to either a single value or multiple (depth, n) values. So, n_data can
        be either a Manning's 'n' value or a list of lists containing differing depth
        and 'n' values (where depth must increase).
        """
        # Single value or depth varying.
        # TUFLOW actually allows 3 input types: a single 'n' value, two sets of 'n' and
        # depth values, and a depth varying series of 'n'.
        # We'll treat the 2 set and depth varying as the same type.
        # Use the class constants SINGLE_N and DEPTH_VARYING_N for n_type
        self.n_type = n_type
        
        # Depth varying 'n' may be supplied in a separate file. Store the path.
        self.filepath = filepath

        # If "VxD:" is prefixed to the Manning's terms the velocity x depth value will be
        # used in the calculations instead of just depth
        self.use_VxD = use_VxD
        
        # Series data. It's all stored the same in depth, roughness table.
        # Single values have two depths - 0 and 100 - with the same 'n' value.
        if n_type == self.SINGLE_N:
            self.n_data = [[0, 100],[n_data, n_data]]
        else:
            if not isinstance(n_data, list):
                raise AttributeError('Materials "n" values format is not correct')
            self.n_data = n_data
        


class TuflowMaterialsLogLaw():
    """Log law depth varying bed resistance
    """
    
    def __init__(self, ks, kappa, n_limit):
        self.ks = ks            # Roughness height
        self.kappa = kappa      # Kappa (0.3 to 0.4, typically 0.38 to 0.42)
        self.n_limit = n_limit  # minim n value (usually for higher depths)
        
        # TUFLOW manual states this as the allowable range
        if self.kappa < 0.3: self.kappa = 0.3
        if self.kappa > 0.4: self.kappa = 0.4


class TuflowMaterialsEntry():
    
    def __init__(self, mat_id, n_data, **kwargs):
        """Setup materials data entry.
        
        Args:
            mat_id (int): unique id for this material.
            n_data: Manning's 'n' or Log law parameters for roughness.
            
        kwargs:
            rainfall_losses=[0,0] (list): 2 item list with initial and continuing rainfall losses.
            hazard_id=-1 (int): (currently unused) id for hazard lookup.
            srf=0 (float): storage reduction factor.
            fract_imperv (float): fraction impervious.
            comment='' (str): comment associated with this material row.
        """
        self.mat_id = mat_id
        self.n_data = None
        self.log_n_data = None
        if isinstance(n_data, TuflowMaterialsMannings):
            self.n_data = n_data
        elif isinstance(n_data, TuflowMaterialsLogLaw):
            self.log_n_data = n_data
        else:
            raise AttributeError(
                'n_data must be either a TuflowMaterialsMannings or TuflowMaterialsLogLaw instance'
            )
            
        self.rainfall_losses = kwargs.get('rainfall_losses', [0,0])
        self.hazard_id = kwargs.get('hazard_id', -1)
        self.srf = kwargs.get('srf', 0)
        self.fract_imperv = kwargs.get('fract_imperv', 0)
        self.comment = kwargs.get('comment', '')
        

class TuflowMaterials():
    """TUFLOW materials file data class.
    
    TUFLOW materials can be one of two formats, tmf or csv. There are many different 
    configuration options possible and these can change based on whether the file is in
    the csv or tmf format.
    
    TUFLOW will accept up to a maximum of 1,000 different material values.
    
    The tmf format can have up to 11 columns; the first two columns are required.
    The column usage can vary across rows, i.e. there can be a different number of values
    in different rows.
    """
    HEADER_COLS_TMF = [
        'material_id', 'n_value', 'init_loss', 'cont_loss', 'y1', 'n1', 'y2', 'n2',
        'reserved', 'srf', 'fract_imperv'
    ]
    DEFAULT_VALS_TMF = [
        None, None, 0, 0, 0, 0, 0, 0, -1, 0, 0
    ]
    HEADER_COLS_CSV = [

    ]
    TYPE_TMF = 0
    TYPE_CSV = 1
    
    def __init__(self, input_path, data, header_names, **kwargs):
        """
        """
        self.input_path = input_path
        ext_split = os.path.splitext(input_path)
        if ext_split[1] == '.csv':
            self.mat_type = self.TYPE_TMF
        elif ext_split[1] == '.tmf':
            self.mat_type = self.TYPE_CSV
        else:
            raise AttributeError ('Materials file must be either tmf or csv format')
        
        self.header_names = header_names
        self.headers_as_read = kwargs.get('headers_as_read', None)
            
        self._check_ids_unique(data)
        self.data = data
            
    def _check_ids_unique(self, data):
        found_ids = []
        for d in data:
            if d.mat_id in found_ids:
                raise ValueError ('Materials IDs must be unique!')
            found_ids.append(d.mat_id)
    

class TuflowBCDbaseEntry():

    # Data type constants
    DT_CSV          = 0     # CSV data used for source
    DT_TS1          = 1     # TS1 data used for source
    DT_CONSTANT     = 2     # No source file, constant value in column_2
    
    def __init__(self, name, source, parent_path=None, **kwargs):
        
        # Work out what kind of 'source' data we are handling
        # TUFLOW requires the extension, so it's safe to use for logic
        if '.ts1' in source:
            self.data_type = self.DT_TS1
        elif '.csv' in source:
            self.data_type = self.DT_CSV
        elif source.strip() == '':
            self.data_type = self.DT_CONSTANT
        else:
            raise ValueError('Source type not currently supported: '.format(source))

        self.name = name
        self.source = source
        self.parent_path = parent_path

        #
        # kwargs
        #
        self.column_1 = kwargs.get('column_1', '')
        self.column_2 = kwargs.get('column_2', '')
        
        # Note: these columns are note used if 'source' is blank
        self.add_col_1 = kwargs.get('add_col_1', 0)
        self.mult_col_2 = kwargs.get('mult_col_2', 1)
        self.add_col_2 = kwargs.get('add_col_2', 0)

        self.column_3 = kwargs.get('column_3', '')
        self.column_4 = kwargs.get('column_4', '')
        
        # Check data requirements
        if self.data_type == self.DT_CONSTANT and not self.column_2:
            raise ValueError('column_2 must contain a value if no source data provided')
        
    
class TuflowBCDbase():
    
    def __init__(self, input_path, data, header_names, **kwargs):
        self.input_path = input_path
        self.header_names = header_names
        self.data = data
        self.headers_as_read = kwargs.get('headers_as_read', None)
        
    def process_data(self):
        pass


class TPCData():
    
    def __init__(self, input_path, data):
        self.input_path = input_path

        # Metadata
        self.format_version = data.get('format version')
        self.units = data.get('units')
        self.run_name = data.get('simulation id')
        self.time_series_format = data.get('time series output format')
        
        # Gis data
        self.gis_plot_points = data.get('gis plot layer points')
        self.gis_plot_lines = data.get('gis plot layer lines')
        self.gis_plot_regions = data.get('gis plot layer regions')
        self.gis_plot_objects = data.get('gis plot layer objects')
        
        # Node/channel counts and information
        self.node_count_1d = data.get('number 1d nodes')
        self.channel_count_1d = data.get('number 1d channel')
        self.node_data_1d = data.get('1d node info')
        self.channel_data_1d = data.get('1d channel info')

        # 1D node results
        self.node_max_1d = data.get('1d node maximums')
        self.water_levels_1d = data.get('1d water levels')
        self.energy_levels_1d = data.get('1d energy levels')
        self.mass_balance_1d = data.get('1d mass balance errors')
        self.node_regime_1d = data.get('1d node regime')
        
        # 1d channel results
        self.channel_max_1d = data.get('1d channel maximums')
        self.flows_1d = data.get('1d flows')
        self.velocities_1d = data.get('1d velocities')
        self.flow_areas_1d = data.get('1d flow areas')
        self.channel_losses_1d = data.get('1d channel losses')
        self.channel_regime_1d = data.get('1d channel regime')

        # Results reporting
        # Points
        self.result_points_count = data.get('number reporting location points')
        self.result_points_water_levels = data.get('reporting location points water levels')
        self.result_points_maximums = data.get('reporting location points maximums')
        # Lines
        self.result_lines_count = data.get('number reporting location lines')
        self.result_lines_water_levels = data.get('reporting location lines water levels')
        self.result_lines_maximums = data.get('reporting location lines maximums')
        # Regions
        self.result_regions_count = data.get('number reporting location regions')
        self.result_regions_water_levels = data.get('reporting location regions water levels')
        self.result_regions_maximums = data.get('reporting location regions maximums')
        
        # TODO: Need to check and handle these a bit differently, I think
        # PO output
        # The variables are a tuple of (relative path, number of results)
        self.po_point_water_level_2d = data.get('2d point water level')
        self.po_line_flow_2d = data.get('2d line flow')


class TuflowResultsNodeDataEntry():
    
    def __init__(self, data, **kwargs):
        self.row_id = data['row_id']                # Unique ID (not sure what this is?)
        self.node = data['node']                    # Node name
        self.bed_level = data['bed_level']          # Bed level (mAD)
        self.top_level = data['top_level']          # Top section data level (mAD)
        self.num_channels = data['num_channels']    # Number of connecting channels
        self.channels = data['channels']            # List of connecting channel names
        
        if self.num_channels != len(self.channels):
            logger.warning('Number of channels does not match channel node list length')
            logger.warning('Setting number of channels to channel list length')
            self.num_channel = self.channels


class TuflowResultsNodeMaxEntry():
    
    def __init__(self, data, **kwargs):
        self.row_id = data['row_id']

        # node or channel name
        self.node = data['id']

        # dict of max values and times for different result types
        self.max_data = data['max_data']


class TuflowResultsNodeData():
    
    def __init__(self, filepath, data, **kwargs):
        self.filepath = filepath
        self.data = data
        
        
class TuflowResultsChannelDataEntry():
    
    def __init__(self, data, **kwargs):
        self.row_id = data['row_id']                # Unique ID (not sure what this is?)
        self.channel = data['channel']              # Channel name
        self.us_node = data['us_node']              # Upstream node reference
        self.ds_node = data['ds_node']              # Downstream node reference
        self.us_channel = data['us_channel']        # Upstream channel reference
        self.ds_channel = data['ds_channel']        # Downstream channel reference
        self.flags = data['flags']                  # Channel type (S, BB, W, etc)
        self.length = data['length']                # Channel length
        self.form_loss = data['form_loss']          # Form loss coefficient
        self.n_or_cd = data['n_or_cd']              # Roughness of discharge coeff, etc
        self.p_slope = data['p_slope']              # % slope
        self.us_invert = data['us_invert']          # Channel upstream invert
        self.ds_invert = data['ds_invert']          # Channel downstream invert
        self.lb_us_invert = data['lb_us_obvert']    # Left bank upstream elevation
        self.rb_us_invert = data['rb_us_obvert']    # Right bank upstream elevation
        self.lb_ds_invert = data['lb_ds_obvert']    # Left bank downstream elevation
        self.rb_ds_invert = data['rb_ds_obvert']    # Right bank downstream elevation
        self.p_blockage = data['p_blockage']        # % blockage


class TuflowResultsChannelData():
    
    def __init__(self, filepath, data, **kwargs):
        self.filepath = filepath
        self.data = data
