'''
tbx_peakflow_calc.py

ArcToolbox script interface to the peak flow tool.
'''

from arcpy import GetParameterAsText
from logic import main

main(
    inlets=GetParameterAsText(0),
    pour_point_field=GetParameterAsText(1),
    flow_dir_raster=GetParameterAsText(2),
    slope_raster=GetParameterAsText(3),
    cn_raster=GetParameterAsText(4),
    precip_table_noaa=GetParameterAsText(5),
    output=GetParameterAsText(6),
    output_catchments=GetParameterAsText(7)
)