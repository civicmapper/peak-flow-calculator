'''
tbx_peakflow_calc.py

ArcToolbox script interface to the peak flow tool.
'''

from arcpy import GetParameterAsText
from logic.gp import prep_cn_raster

prep_cn_raster(
    dem=GetParameterAsText(1),
    curve_number_raster=GetParameterAsText(0),
    out_cn_raster=GetParameterAsText(2),
    out_coor_system=GetParameterAsText(3)
)