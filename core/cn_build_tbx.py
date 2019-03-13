'''
cn_build_tbx.py

ArcToolbox script interface to the Curve Number Raster Builder script.

Used when you need to build a Curve Number Raster from scratch, using landcover, soils, and curve number lookup CSV.
'''

from arcpy import GetParameterAsText
from logic.gp import build_cn_raster

build_cn_raster(
    landcover_raster=GetParameterAsText(0),
    lookup_csv=GetParameterAsText(3),
    soils_polygon = GetParameterAsText(1),
    soils_hydrogroup_field = GetParameterAsText(2),
    reference_raster=GetParameterAsText(4),
    out_cn_raster=GetParameterAsText(5)
)