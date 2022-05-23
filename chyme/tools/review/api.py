"""
 Summary:
     API entry points for tools in the review package.

 Author:
    Duncan Runnacles

 Created:
    22 May 2022
"""

from chyme.tuflow.loader import TuflowLoader
from . import files as review_files
from . import sections as review_sections

def check_files(model):
    
    # TODO: Obviously shouldn't be a TuflowLoader by this point!
    if isinstance(model, TuflowLoader):
        file_check = review_files.check_files_tuflow(model)
        
        # TODO: file check should maybe be a class with a standard interface that we can
        #       require for different model types?
        return file_check
    

def find_results_files(results_path):
    return review_files.find_tuflow_results(results_path)


def map_model_directory(root_folder):
    return review_files.map_directory(root_folder)


def check_sections(model):
    
    # TODO: Obviously shouldn't be a TuflowLoader by this point!
    if isinstance(model, TuflowLoader):
        return review_sections.check_sections_tuflow(model)