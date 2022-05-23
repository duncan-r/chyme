"""
 Summary:
    Validation functions for model cross sections.

 Author:
    Duncan Runnacles

 Created:
    22 May 2022
"""

def check_sections_tuflow(model, include_deactivated=False):
    
    sections = []
    for part in model.components['control_1d'].parts:
        if part.command.value == 'read gis table links':
            for f in part.files.files:
                if f.data and 'source' in f.data.associated_data:
                    sections += f.data.associated_data['source']
    
    widths = check_width(sections)
    return {
        'widths': widths
    }


def check_conveyance(sections, include_deactivated=False):
    pass


def check_width(sections, include_deactivated=False):
    widths = {}
    if include_deactivated:
        for s in sections:
            widths[s.metadata.name] = (
                s.cross_section.xh_series.points[-1][0] -
                s.cross_section.xh_series.points[0][0]
            )
    else:
        for s in sections:
            widths[s.metadata.name] = (
                s.cross_section.xh_series.points[-1][0] -
                s.cross_section.xh_series.points[0][0]
            )
    
    return widths

def check_banktops(sections, include_deactivated=False):
    pass


def check_roughness(sections, include_deactivated=False):
    pass


def hydraulic_properties(sections, include_deactivated=False):
    pass


def chainage(model):
    pass
