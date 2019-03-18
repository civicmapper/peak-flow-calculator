'''
peakflow2_tbx.py

ArcToolbox script interface to the peak flow tool.
'''

from arcpy import GetParameterAsText
from logic import main

main(
    inlets=GetParameterAsText(0),
    flow_dir_raster=GetParameterAsText(1),
    slope_raster=GetParameterAsText(2),
    cn_raster=GetParameterAsText(3),
    precip_table_noaa=GetParameterAsText(4),
    output=GetParameterAsText(5),
    output_catchments=GetParameterAsText(6)
)