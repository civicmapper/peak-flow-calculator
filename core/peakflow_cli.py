'''
Peak-flow-calculator command line interface
'''

# application
from logic import main
from logic.gp import derive_from_dem, prep_cn_raster

# main click entry point
@click.group()
def calc():
    pass

@calc.command()
@calc.argument('inlets')
@calc.argument('flow_dir_raster')
@calc.argument('slope_raster')
@calc.argument('cn_raster')
@calc.argument('precip_table_noaa')
@calc.option(
    'output',
    default=None,
    help="output feature class (e.g., .shp file, fgdb feature class, etc...anything ArcPy can write to."
)
@calc.option(
    'pour_point_field',
    default='OBJECTID',
    help='field containing unique id of inlets'
)
def lite(inlets, flow_dir_raster, slope_raster, cn_raster, precip_table_noaa, output, pour_point_field):
    """
    Peak-Flow Calculator "Lite". Use with pre-calculated slope and flow direction rasters.
    """
    output_data = main(
        inlets=inlets,
        pour_point_field=pour_point_field,
        flow_dir_raster=flow_dir_raster,
        slope_raster=slope_raster,
        cn_raster=cn_raster,
        precip_table_noaa=precip_table_noaa,
        output=output
    )
    return output_data

@calc.command()
@calc.argument('inlets')
@calc.argument('dem')
@calc.argument('cn_raster')
@calc.argument('precip_table_noaa')
@calc.option(
    'output',
    default=None,
    help="output feature class (e.g., .shp file, fgdb feature class, etc...anything ArcPy can write to."
)
@calc.option(
    'pour_point_field',
    default='OBJECTID',
    help='field containing unique id of inlets'
)
def full(inlets, dem, cn_raster, precip_table_noaa, pour_point_field, output):
    """
    Peak-Flow Calculator "Full". Use to automatically calculate flow direction and slope from DEM.
    """

    msg('Deriving flow direction and slop from DEM...')
    derived_rasters = derive_from_dem(dem=dem)
    flow_dir_raster = derived_rasters['flow_direction_raster']
    slope_raster = derived_rasters['slope_raster']

    output_data = main(
        inlets=inlets,
        pour_point_field=pour_point_field,
        flow_dir_raster=flow_dir_raster,
        slope_raster=slope_raster,
        cn_raster=cn_raster,
        precip_table_noaa=precip_table_noaa,
        output=output
    )
    return output_data
        
    return

@calc.command()
@calc.argument('original_cn_raster')
@calc.argument('dem')
@calc.argument('output_cn_raster')
@calc.option(
    'crs',
    default="PROJCS['NAD_1983_StatePlane_Pennsylvania_South_FIPS_3702_Feet',GEOGCS['GCS_North_American_1983',DATUM['D_North_American_1983',SPHEROID['GRS_1980',6378137.0,298.257222101]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]],PROJECTION['Lambert_Conformal_Conic'],PARAMETER['False_Easting',1968500.0],PARAMETER['False_Northing',0.0],PARAMETER['Central_Meridian',-77.75],PARAMETER['Standard_Parallel_1',39.93333333333333],PARAMETER['Standard_Parallel_2',40.96666666666667],PARAMETER['Latitude_Of_Origin',39.33333333333334],UNIT['Foot_US',0.3048006096012192]]", 
    help='coordinate system string'
)
def prepare_cn_raster(original_cn_raster, dem, output_cn_raster, crs):
    """
    Resamples and reprojects a curve number raster to match the DEM's extents,
    cell size; uses a DEM as snap raster.
    """
    prep_cn_raster(
        dem=dem,
        curve_number_raster=original_cn_raster,
        out_cn_raster=output_cn_raster,
        out_coor_system=crs
    )
    return