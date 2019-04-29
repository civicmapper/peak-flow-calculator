'''
gp.py

runs ArcPy geoprocessing tools

'''
# standard library
import os, time
# ArcPy imports
from arcpy import Describe, Raster
from arcpy import GetCount_management, Clip_management, Dissolve_management, CopyFeatures_management
from arcpy import JoinField_management, MakeTableView_management
from arcpy import BuildRasterAttributeTable_management, ProjectRaster_management
from arcpy import RasterToPolygon_conversion, TableToTable_conversion, PolygonToRaster_conversion
from arcpy.sa import Watershed, FlowLength, Slope, SetNull, ZonalStatisticsAsTable, FlowDirection, Con, CellStatistics #, ZonalGeometryAsTable
from arcpy.da import SearchCursor
from arcpy import env
from arcpy import SetProgressor, SetProgressorLabel, SetProgressorPosition, ResetProgressor

# third party tools
import petl as etl

# this package
from .utils import so, msg, clean

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

def build_cn_raster(
    landcover_raster,
    lookup_csv,
    soils_polygon,
    soils_hydrogroup_field="SOIL_HYDRO",
    reference_raster=None,
    out_cn_raster=None
):
    """Build a curve number raster from landcover raster, soils polygon, and a crosswalk between 
    landcover classes, soil hydro groups, and curve numbers.

    :param lookup_csv: [description]
    :type lookup_csv: [type]
    :param landcover_raster: [description]
    :type landcover_raster: [type]
    :param soils_polygon: polygon containing soils with a hydro classification. 
    :type soils_polygon: [type]
    :param soils_hydrogroup_field: [description], defaults to "SOIL_HYDRO" (from the NCRS soils dataset)
    :type soils_hydrogroup_field: str, optional
    :param out_cn_raster: [description]
    :type out_cn_raster: [type]    
    """

    # GP Environment ----------------------------
    msg("Setting up GP Environment...")
    # if reference_raster is provided, we use it to set the GP environment for 
    # subsequent raster operations
    if reference_raster: 
        if not isinstance(reference_raster,Raster):
            # read in the reference raster as a Raster object.
            reference_raster = Raster(reference_raster)
    else:
        reference_raster = Raster(landcover_raster)

    # set the snap raster, cell size, and extent, and coordinate system for subsequent operations
    env.snapRaster = reference_raster
    env.cellSize = reference_raster.meanCellWidth
    env.extent = reference_raster
    env.outputCoordinateSystem = reference_raster
    
    cs = env.outputCoordinateSystem.exportToString()

    # SOILS -------------------------------------
    
    msg("Processing Soils...")
    # read the soils polygon into a raster, get list(set()) of all cell values from the landcover raster
    soils_raster_path = so("soils_raster")
    PolygonToRaster_conversion(soils_polygon, soils_hydrogroup_field, soils_raster_path, "CELL_CENTER")
    soils_raster = Raster(soils_raster_path)

    # use the raster attribute table to build a lookup of raster values to soil hydro codes
    # from the polygon (that were stored in the raster attribute table after conversion)
    if not soils_raster.hasRAT:
        msg("Soils raster does not have an attribute table. Building...", "warning")
        BuildRasterAttributeTable_management(soils_raster, "Overwrite")
    # build a 2D array from the RAT
    fields = ["Value", soils_hydrogroup_field]
    rows = [fields]
    # soils_raster_table = MakeTableView_management(soils_raster_path)
    with SearchCursor(soils_raster_path, fields) as sc:
        for row in sc:
            rows.append([row[0], row[1]])
    # turn that into a dictionary, where the key==soil hydro text and value==the raster cell value
    lookup_from_soils = {v: k for k, v in etl.records(rows)}
    # also capture a list of just the values, used to iterate conditionals later
    soil_values = [v['Value'] for v in etl.records(rows)]

    # LANDCOVER ---------------------------------
    msg("Processing Landcover...")
    if not isinstance(landcover_raster, Raster):
        # read in the reference raster as a Raster object.
        landcover_raster_obj = Raster(landcover_raster)
    landcover_values = []
    with SearchCursor(landcover_raster, ["Value"]) as sc:
        for row in sc:
            landcover_values.append(row[0])

    # LOOKUP TABLE ------------------------------
    msg("Processing Lookup Table...")
    # read the lookup csv, clean it up, and use the lookups from above to limit it to just
    # those values in the rasters
    t = etl\
        .fromcsv(lookup_csv)\
        .convert('utc', int)\
        .convert('cn', int)\
        .select('soil', lambda v: v in lookup_from_soils.keys())\
        .convert('soil', lookup_from_soils)\
        .select('utc', lambda v: v in landcover_values)
    
    # This gets us a table where we the landcover class (as a number) corresponding to the 
    # correct value in the converted soil raster, with the corresponding curve number.

    # DETERMINE CURVE NUMBERS -------------------
    msg("Assigning Curve Numbers...")
    # Use that to reassign cell values using conditional map algebra operations
    cn_rasters = []
    for rec in etl.records(t):
        cn_raster_component = Con((landcover_raster_obj == rec.utc) & (soils_raster == rec.soil), rec.cn, 0)
        cn_rasters.append(cn_raster_component)

    cn_raster = CellStatistics(cn_rasters, "MAXIMUM")

    # REPROJECT THE RESULTS -------------------
    msg("Reprojecting and saving the results....")
    if not out_cn_raster:
        out_cn_raster = so("cn_raster","random","in_memory")

    ProjectRaster_management(
        in_raster=cn_raster,
        out_raster=out_cn_raster,
        out_coor_system=cs,
        resampling_type="NEAREST",
        cell_size=env.cellSize
    )
    
    # cn_raster.save(out_cn_raster)
    return out_cn_raster


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
    msg("...catchments raster saved:\n\t{0}".format(catchments_save))
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
    length_conv_factor=1,
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
    catchment_count = int(GetCount_management(catchment_table).getOutput(0))
    with SearchCursor(catchment_table, [raster_field]) as catchments:

        # TODO: implement multi-processing for this loop.
        
        ResetProgressor()
        SetProgressor('step', "Mapping flow length for catchments", 0, catchment_count, 1)
        # msg("Mapping flow length for catchments")

        for idx, each in enumerate(catchments):
            this_id = each[0]
            # msg("{0}".format(this_id))
            # calculate flow length for each "zone" in the raster
            fl_max = calc_catchment_flowlength_max(
                catchment_areas,
                this_id,
                flow_direction_raster,
                length_conv_factor
            )
            if this_id in results.keys():
                results[this_id]["max_fl"] = clean(fl_max)
            else:
                results[this_id] = {"max_fl": clean(fl_max)}
            SetProgressorPosition()
        ResetProgressor()

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
                results[this_id]["avg_cn"] = clean(this_area)
            else:
                results[this_id] = {"avg_cn": clean(this_area)}
    
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
                results[this_id]["avg_slope"] = clean(this_area)
            else:
                results[this_id] = {"avg_slope": clean(this_area)}
    
    # calculate area of each catchment
    #ZonalGeometryAsTable(catchment_areas,"Value","output_table") # crashes like an mfer
    cp = so("catchmentpolygons","timestamp","in_memory")
    #RasterToPolygon copies our ids from raster_field into "gridcode"
    RasterToPolygon_conversion(catchment_areas, cp, "NO_SIMPLIFY", raster_field)

    # Dissolve the converted polygons, since some of the raster zones may have corner-corner links
    if not out_catchment_polygons:
        cpd = so("catchmentpolygonsdissolved","timestamp","in_memory")
    else:
        cpd = out_catchment_polygons
    Dissolve_management(
        in_features=cp,
        out_feature_class=cpd,
        dissolve_field="gridcode",
        multi_part="MULTI_PART"
    )

    # get the area for each record, and push into results object
    with SearchCursor(cpd,["gridcode","SHAPE@AREA"]) as c:
        for r in c:
            this_id = r[0]
            this_area = r[1] * area_conv_factor
            if this_id in results.keys():
                results[this_id]["area_up"] = clean(this_area)
            else:
                results[this_id] = {"area_up": clean(this_area)}
    
    # flip results object into a records-style array of dictionaries
    # (this makes conversion to table later on simpler)
    # msg(results,"warning")
    records = []
    for k in results.keys():
        record = {
            "area_up":0,
            "avg_slope":0,
            "max_fl":0,
            "avg_cn":0,
            "tc_hr":0
        }
        for each_result in record.keys():
            if each_result in results[k].keys():
                record[each_result] = results[k][each_result]
        record["id"] = k
        records.append(record)
    
    if out_catchment_polygons:
        return records, cpd
    else:
        return records, None

def calc_catchment_flowlength_max(
    catchment_area_raster,
    zone_value,
    flow_direction_raster,
    length_conv_factor #???
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
    #TODO: convert length to ? using length_conv_factor (detected from the flow direction raster)
    fl_max = fl_max * length_conv_factor
        
    return fl_max