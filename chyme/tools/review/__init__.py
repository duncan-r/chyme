
import logging
logger = logging.getLogger(__name__)

GDAL_AVAILABLE = True
try:
    from osgeo import gdal
    from osgeo import ogr
except ImportError as e:
    GDAL_AVAILABLE = False
    
OGR_DRIVERS = {
    'shp': 'ESRI Shapefile',
    'mif': 'MapInfo File',
    'mid': 'MapInfo File',
    'sqlite': 'SQLite',
    'sqlite3': 'SQLite',
}

