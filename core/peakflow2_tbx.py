'''
peakflow2_tbx.py

ArcToolbox script interface to the peak flow tool.

Includes an additional argument for inputing a pre-calculated basin layer, which speeds up the execution time.
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