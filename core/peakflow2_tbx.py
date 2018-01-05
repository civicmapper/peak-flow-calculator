'''
tbx_peakflow_calc.py

ArcToolbox script interface to the peak flow tool.
'''

from arcpy import GetParameterAsText
from logic import main

main(
    inlets=GetParameterAsText(0),
    pour_point_field=GetParameterAsText(1),
    input_watershed_raster=GetParameterAsText(2),
    flow_dir_raster=GetParameterAsText(3),
    slope_raster=GetParameterAsText(4),
    cn_raster=GetParameterAsText(5),
    precip_table_noaa=GetParameterAsText(6),
    output=GetParameterAsText(7),
    output_catchments=GetParameterAsText(8)
)