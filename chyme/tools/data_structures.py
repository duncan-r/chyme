"""
 Summary:
    

 Author:
    Duncan Runnacles

 Created:
    7 May 2022
"""

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
        # self.data = data
        self.headers_as_read = kwargs.get('headers_as_read', None)
            
        self._check_ids_unique(data)
        self.data = data
            
    def _check_ids_unique(self, data):
        found_ids = []
        for d in data:
            if d.mat_id in found_ids:
                raise ValueError ('Materials IDs must be unique!')
            found_ids.append(d.mat_id)
    
    
class BCDbase():
    
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
        self.data = data
        
        
