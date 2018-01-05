'''
gp.py

runs ArcPy geoprocessing tools

'''
# standard library
import os, time
# ArcPy imports
from arcpy import Describe, Raster
from arcpy import GetCount_management, BuildRasterAttributeTable_management, MakeTableView_management, ProjectRaster_management, Clip_management
from arcpy import RasterToPolygon_conversion, TableToTable_conversion, CopyFeatures_management, JoinField_management
from arcpy.sa import Watershed, FlowLength, Slope, SetNull, ZonalStatisticsAsTable, FlowDirection#, ZonalGeometryAsTable
from arcpy.da import SearchCursor
from arcpy import env

# this package
from utils import so, msg

# ----------------------------------------------------------------------------
# HELPERS

def load_csv(csv):
    """loads a csv into the ArcMap scratch geodatabase. Use for temporary files only.
    Output: path to the imported csv
    """
    t = so("csv","random","fgdb")
    TableToTable_conversion(
        in_rows=csv, 
        out_path=os.path.dirname(t), 
        out_name=os.path.basename(t)
    )
    return t

def join_to_copy(in_data, out_data, join_table, in_field, join_field):
    """given an input feature, make a copy, then execute a join on that copy.
    Return the copy.
    """
    msg(in_data)
    msg(out_data)
    msg(join_table)
    msg(in_field)
    msg(join_field)
    # copy the inlets file
    CopyFeatures_management(
        in_features=in_data, 
        out_feature_class=out_data
    )
    # join the table to the copied file
    JoinField_management(
        in_data=out_data, 
        in_field=in_field, 
        join_table=join_table, 
        join_field=join_field
    )
    return out_data

# ----------------------------------------------------------------------------
# GEOPROCESSING WRAPPERS

def prep_cn_raster(
    dem,
    curve_number_raster,
    out_cn_raster=None,
    out_coor_system="PROJCS['NAD_1983_StatePlane_Pennsylvania_South_FIPS_3702_Feet',GEOGCS['GCS_North_American_1983',DATUM['D_North_American_1983',SPHEROID['GRS_1980',6378137.0,298.257222101]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]],PROJECTION['Lambert_Conformal_Conic'],PARAMETER['False_Easting',1968500.0],PARAMETER['False_Northing',0.0],PARAMETER['Central_Meridian',-77.75],PARAMETER['Standard_Parallel_1',39.93333333333333],PARAMETER['Standard_Parallel_2',40.96666666666667],PARAMETER['Latitude_Of_Origin',39.33333333333334],UNIT['Foot_US',0.3048006096012192]]"
    ):
    """
    Clip, reproject, and resample the curve number raster to match the DEM.
    Ensure everything utilizes the DEM as the snap raster.
    The result is returned in a dictionary referencing an ArcPy Raster object
    for the file gdb location of the processed curve number raster.
    
    For any given study area, this will only need to be run once.
    """
    
    # make the DEM an ArcPy Raster object, so we can get the raster properties
    if not isinstance(dem,Raster):
        dem = Raster(dem)
    
    msg("Clipping...")
    # clip the curve number raster, since it is likely for a broader study area
    clipped_cn = so("cn_clipped")
    Clip_management(
        in_raster=curve_number_raster,
        out_raster=clipped_cn,
        in_template_dataset=dem,
        clipping_geometry="NONE",
        maintain_clipping_extent="NO_MAINTAIN_EXTENT"
    )
    
    # set the snap raster for subsequent operations
    env.snapRaster = dem
    
    # reproject and resample he curve number raster to match the dem
    if not out_cn_raster:
        prepped_cn = so("cn_prepped")
    else:
        prepped_cn = out_cn_raster
    msg("Projecting and Resampling...")
    ProjectRaster_management(
        in_raster=clipped_cn,
        out_raster=prepped_cn,
        out_coor_system=out_coor_system,
        resampling_type="NEAREST",
        cell_size=dem.meanCellWidth
    )
    
    return {
        "curve_number_raster": Raster(prepped_cn)
    }

def derive_from_dem(dem):
    """derive slope and flow direction from a DEM.
    Results are returned in a dictionary that contains references to
    ArcPy Raster objects stored in the "in_memory" (temporary) workspace
    """
    
    # set the snap raster for subsequent operations
    env.snapRaster = dem
    
    # calculate flow direction for the whole DEM
    flowdir = FlowDirection(in_surface_raster=dem, force_flow="NORMAL")
    flow_direction_raster = so("flowdir","random","in_memory")
    flowdir.save(flow_direction_raster)
    
    # calculate slope for the whole DEM
    slope = Slope(in_raster=dem, output_measurement="PERCENT_RISE", method="PLANAR")
    slope_raster = so("slope","random","in_memory")
    slope.save(slope_raster)

    return {
        "flow_direction_raster": Raster(flow_direction_raster),
        "slope_raster": Raster(slope_raster),
    }

def catchment_delineation(inlets, flow_direction_raster, pour_point_field):
    """    
    Delineate the catchment area(s) for the inlet(s). Also provide back how many
    catchments we're dealing with so we can handle iteration accordingly.
    
    Input:
        - inlets: point shapefile or feature class representing inlet location(s)
            from which catchment area(s) will be determined. Can be one or
            many inlets.
    
    Output:
        - a python dictionary structured as follows:
            {
            "catchments": <path to the catchments raster created by the
            Arcpy.sa Watershed function>,
            "count": <count (int) of the number of inlets/catchments>
            }
    """

    # delineate the watershed(s) for the inlets. This is the standard spatial analyst watershed function
    catchments = Watershed(
        in_flow_direction_raster=flow_direction_raster,
        in_pour_point_data=inlets,
        pour_point_field=pour_point_field
    )
    # save the catchments layer to the fgdb set by the arcpy.env.scratchgdb setting)
    catchments_save = so("catchments","timestamp","fgdb")
    catchments.save(catchments_save)
    msg("catchments raster saved: {0}".format(catchments_save))
    # get count of how many watersheds we should have gotten (# of inlets)
    count = int(GetCount_management(inlets).getOutput(0))
    # return a dictionary containing ref. to the scratch catchments layer and the count of catchments
    return {"catchments": catchments, "count": count}

def derive_data_from_catchments(
    catchment_areas,
    flow_direction_raster,
    slope_raster,
    curve_number_raster,
    area_conv_factor=0.00000009290304,
    out_catchment_polygons=None
    ):
    """
    For tools that handle multiple inputs quickly, we execute here (e.g., zonal
    stats). For those we need to run on individual catchments, this parses the
    catchments raster and passes individual catchments, along with other required 
    data, to the calc_catchment_flowlength_max function.

    area_conversion_factor: for converting the area of the catchments to Sq. Km, which is 
        expected by the core business logic. By default, the factor converts from square feet 
    out_catchment_polygons: will optionally return a catchment polygon feature class.

    Output: an array of records containing info about each inlet's catchment, e.g.:
        [
            {
                "id": <ID value from pour_point_field (spec'd in catchment_delineation func)> 
                "area_sqkm": <area of inlet's catchment in square km>
                "avg_slope": <average slope of DEM in catchment>
                "avg_cn": <average curve number in the catchment>
                "max_fl": <maximum flow length in the catchment>
            },
            {...},
            ...
         ]
    """
    raster_field = "Value"

    # store the results, keyed by a catchment ID (int) that comes from the
    # catchments layer gridcode
    results = {}
    
    # make a raster object with the catchment raster
    if not isinstance(catchment_areas,Raster):
        c = Raster(catchment_areas)
    else:
        c = catchment_areas
    # if the catchment raster does not have an attribute table, build one
    if not c.hasRAT:
        BuildRasterAttributeTable_management(c, "Overwrite")

    # make a table view of the catchment raster
    catchment_table = 'catchment_table'
    MakeTableView_management(c,catchment_table) #, {where_clause}, {workspace}, {field_info})

    # calculate flow length for each zone. Zones must be isolated as individual
    # rasters for this to work. We handle that with calc_catchment_flowlength_max()
    # using the table to get the zone values...
    with SearchCursor(catchment_table, [raster_field]) as catchments:
        # TODO: implement multi-processing for this loop.
        msg("Mapping flow length for catchment:")
        for each in catchments:
            this_id = each[0]
            msg("{0}".format(this_id))
            # calculate flow length for each "zone" in the raster
            fl_max = calc_catchment_flowlength_max(
                catchment_areas,
                this_id,
                flow_direction_raster
            )
            if this_id in results.keys():
                results[this_id]["max_fl"] = fl_max
            else:
                results[this_id] = {"max_fl": fl_max}

    # calculate average curve number within each catchment for all catchments
    table_cns = so("cn_zs_table","timestamp","fgdb")
    msg("CN Table: {0}".format(table_cns))
    ZonalStatisticsAsTable(catchment_areas, raster_field, curve_number_raster, table_cns, "DATA", "MEAN")
    # push table into results object
    with SearchCursor(table_cns,[raster_field,"MEAN"]) as c:
        for r in c:
            this_id = r[0]
            this_area = r[1]
            if this_id in results.keys():
                results[this_id]["avg_cn"] = this_area
            else:
                results[this_id] = {"avg_cn": this_area}
    
    # calculate average slope within each catchment for all catchments
    table_slopes = so("slopes_zs_table","timestamp","fgdb")
    msg("Slopes Table: {0}".format(table_slopes))
    ZonalStatisticsAsTable(catchment_areas, raster_field, slope_raster, table_slopes, "DATA", "MEAN")
    # push table into results object
    with SearchCursor(table_slopes,[raster_field,"MEAN"]) as c:
        for r in c:
            this_id = r[0]
            this_area = r[1]
            if this_id in results.keys():
                results[this_id]["avg_slope"] = this_area
            else:
                results[this_id] = {"avg_slope": this_area}
    
    # calculate area of each catchment
    #ZonalGeometryAsTable(catchment_areas,"Value","output_table") # crashes like an mfer
    if not out_catchment_polygons:
        cp = so("catchmentpolygons","timestamp","in_memory")
    else:
        cp = out_catchment_polygons
    RasterToPolygon_conversion(catchment_areas, cp, "NO_SIMPLIFY", raster_field)
    # push table into results object
    with SearchCursor(cp,["gridcode","SHAPE@AREA"]) as c:
        for r in c:
            this_id = r[0]
            this_area = r[1] * area_conv_factor
            if this_id in results.keys():
                results[this_id]["area_sqkm"] = this_area 
            else:
                results[this_id] = {"area_sqkm": this_area}
    
    # flip results object into a records-style array of dictionaries
    # (this makes conversion to table later on simpler)
    # msg(results,"warning")
    records = []
    for k in results.iterkeys():
        record = {
            "area_sqkm":"",
            "avg_slope":"",
            "max_fl":"",
            "avg_cn":""
        }
        for each_result in record.keys():
            if each_result in results[k].keys():
                record[each_result] = results[k][each_result]
        record["id"] = k
        records.append(record)
    
    if out_catchment_polygons:
        return records, cp
    else:
        return records, None


def calc_catchment_flowlength_max(
    catchment_area_raster,
    zone_value,
    flow_direction_raster
    ):
    
    """
    Derives flow length for a *single catchment area using a provided zone
    value (the "Value" column of the catchment_area_raster's attr table).
    
    Inputs:
        catchment_area: *raster* representing the catchment area(s)
        zone_value: an integer from the "Value" column of the
            catchment_area_raster's attr table.
        flow_direction_raster: flow direction raster for the broader
    outputs:
        returns the 
    """
    # use watershed raster to clip flow_direction, slope rasters
    # make a raster object with the catchment_area_raster raster
    if not isinstance(catchment_area_raster,Raster):
        c = Raster(catchment_area_raster)
    else:
        c = catchment_area_raster    
    # clip the flow direction raster to the catchment area (zone value)
    fd = SetNull(c != zone_value, flow_direction_raster)
    # calculate flow length
    fl = FlowLength(fd,"UPSTREAM")
    # determine maximum flow length
    fl_max = fl.maximum
        
    return fl_max