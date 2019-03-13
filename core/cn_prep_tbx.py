'''
cn_prep_tbx.py

ArcToolbox script interface to Curve Number Raster preparation script.

Used when you already have a curve number raster, but need to snap it to the DEM.
'''

from arcpy import GetParameterAsText
from logic.gp import prep_cn_raster

prep_cn_raster(
    dem=GetParameterAsText(1),
    curve_number_raster=GetParameterAsText(0),
    out_cn_raster=GetParameterAsText(2),
    out_coor_system=GetParameterAsText(3)
)