"""
 Summary:
     Functions for validating files in model.

 Author:
    Duncan Runnacles

 Created:
    22 May 2022
"""

import os

                
def map_directory(root_folder):
    """Build up a folder heirachy of files and locations from a root folder.
    
    Note: this is going to get BIG and SLOW if the root is too high up the tree!
    
    Fairly simple implementation at the moment. Probably need a directory map as well to
    store the folders - in a tree of suchlike - for quick lookup.
    """
    class FileMap():
        
        def __init__(self, filename, root_folder, parents=None):
            self.filename = filename
            self.root_folder = root_folder
            self.parents = parents if isinstance(parents, list) else []
            
        @property
        def absolute_path(self):
            return os.path.join(
                self.root_folder, os.path.join(self.parents), self.filename
            )
            
        def has_parent(self, folders, check_for_all=True):
            """Checks whether any of the given folders and in the parents list.
            
            Checks parents list for a match to folders. Works from the end of the parents
            list backwards.
            
            Args:
                folders (list): folder name strings to check.
                check_for_all=True (bool): if True, all given folders must be in the
                    parents. Otherwise a single match from the list will return True.
            
            Return:
                bool - True if one or more of folders are found in parents.
            """
            found_count = 0
            for i in range(len(self.parents), 0, -1):
                if self.parents[i] in folders:
                    found_count += 1
                if not check_for_all and found_count > 0:
                    return True
                elif found_count == len(folders):
                    return True
            return False

    
    if not os.path.isdir(root_folder):
        raise ValueError('root_folder is not a directory')
    
    filemap = []

    normroot = os.path.normpath(root_folder)
    for root, folders, filenames in os.walk(root_folder):
        norm_folder = os.path.normpath(root)
        
        parents = []
        if norm_folder != normroot:
            norm_folder = norm_folder.replace(normroot, '')
            # Remove the leading value caused by leading path separator
            parents = norm_folder.split(os.path.sep)[1:]
        
        for f in filenames:
            filemap.append(FileMap(
                f, normroot, parents=parents
            ))
            
    return filemap


def check_files_tuflow(model):
    """File validation and sanity check for TUFLOW models.
    
    Abstract the implementation away from the API. The expectation is that this will never
    be called directly; it should have a wrapper function in the API. We can then maintain
    consistency in the API and still do what we want here.

    TODO: This will need re-writing when we sort out the model setup.
    """
    
    failed = []

    # Check 1D files
    for part in model.components['control_1d'].parts:
        if part.files:
            for f in part.files.files:
                if part.command.value == 'output folder' or part.command.value == 'write check files':
                    continue

                if not os.path.exists(f.path.absolute_path):
                    failed.append({
                        'absolute_path': f.path.absolute_path,
                        'command_line': part.load_data.raw_line,
                        'parent_file': part.load_data.parent_path,
                    })
                    
                if part.command.value == 'read gis table links':
                    source_index = f.data.attribute_lookup['Source']
                    for field in f.data.field_data:
                        source_abs = os.path.join(
                            os.path.dirname(f.path.absolute_path), field['fields'][source_index]
                        )
                        if not os.path.exists(source_abs):
                            failed.append({
                                'absolute_path': source_abs,
                                'command_line': part.load_data.raw_line,
                                'parent_file': f.path.absolute_path
                            })

    # Check 2D files
    for domain, domain_parts in model.components['control_2d'].parts.items():
        for part in domain_parts:
            if part.files:
                for f in part.files.files:
                    if part.command.value == 'output folder' or part.command.value == 'write check files':
                        continue

                    if not os.path.exists(f.path.absolute_path):
                        failed.append({
                            'absolute_path': f.path.absolute_path,
                            'command_line': part.load_data.raw_line,
                            'parent_file': part.load_data.parent_path,
                        })

    # Check Geometry Files
    for part in model.components['geometry'].parts:
        if part.files:
            for f in part.files.files:

                if not os.path.exists(f.path.absolute_path):
                    failed.append({
                        'absolute_path': f.path.absolute_path,
                        'command_line': part.load_data.raw_line,
                        'parent_file': part.load_data.parent_path,
                    })

    # Check Boundary Files
    for part in model.components['boundary'].parts:
        if part.files:
            for f in part.files.files:

                if not os.path.exists(f.path.absolute_path):
                    failed.append({
                        'absolute_path': f.path.absolute_path,
                        'command_line': part.load_data.raw_line,
                        'parent_file': part.load_data.parent_path,
                    })
                        
    return failed


def find_tuflow_results(results_path):
    
    results_files = []
    file_types = ['.csv', '.tpc', '.xmdf', '.dat', '.shp', '.mif', '.mid']
    for root, folders, filenames in os.walk(results_path):
        for f in filenames:
            extension = os.path.splitext(f)
            if len(extension) > 1:
                if extension[1] in file_types:
                    results_files.append(os.path.join(root, f)) 
    
    return results_files
        

        
        