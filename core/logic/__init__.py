"""

Core - drainage runoff / peak flow evaluation module

The functions here is called from ArcToolbox script tools and the CLI

---

# Some notes 

- Inlets: these are iteratively created prior to running the tool
- Slope Raster: one time for entire study area, *derived from non-corrected DEM*
- Curve No. Raster: this comes from external data source. Could be calculated 
    from landcover and soil, or straight input from user.
- Precipitation table: relies on NOAA precip table (specifically, the format of the data)

Output is a derived inlet/point file with runoff estimates by rainfall event
appended to each table

- calculate max flow length catchment area
- calculate average slope of catchment area
- calculate time of concentration from max flow len, average slope

efficiency possible by calculating slope for broader area ahead of time,
and just getting average for study area from that (e.g., w/ zonal stats)

This information is then associated with the inlet/culvert of each
catchment_area
"""

# -----------------------------------------------------------------------------
# IMPORTS
#

# standard library imports
import os
from collections import OrderedDict

# dependencies
from arcpy import AddMessage, AddWarning, AddError, Describe, ListEnvironments, Raster
from arcpy import CopyFeatures_management, JoinField_management
from arcpy import FeatureSet
from arcpy import env
from arcpy import SetProgressor, SetProgressorLabel, SetProgressorPosition, ResetProgressor

# application imports
from .data_io import precip_table_etl_noaa
from .gp import prep_cn_raster, load_csv, join_to_copy, derive_data_from_catchments, catchment_delineation
from .calc import calculate_tc, calculate_peak_flow
from .utils import so, msg, attempt_pkg_install

# add'l dependencies, not included with ArcMap's Python installtion;
# this is here in case user hasn't attempted `pip install -r requirements.txt`
# try:
import petl as etl
# except:
    # attempt_pkg_import('petl>=1.1')
# try:    
# import click
# except:
    # attempt_pkg_import('click>=6')
# try:
import pint
# except:
    # attempt_pkg_import('pint>=0.8.1')


# -----------------------------------------------------------------------------
# Globals
# 

units = pint.UnitRegistry()

QP_HEADER = ['Y1','Y2','Y5','Y10','Y25','Y50','Y100','Y200','Y500','Y1000']
ANALYSIS_FIELDS = ['avg_slope', 'avg_cn', 'tc_hr', 'area_up', 'max_fl']
OUTPUT_FIELDS = QP_HEADER + ANALYSIS_FIELDS

# -----------------------------------------------------------------------------
# Application controller
#

def main(
    inlets, 
    flow_dir_raster, 
    slope_raster, 
    cn_raster, 
    precip_table_noaa, 
    output, 
    output_catchments=None, 
    pour_point_field=None, 
    input_watershed_raster=None, 
    area_conv_factor=0.00000009290304, 
    length_conv_factor=1,
    output_fields=OUTPUT_FIELDS,
    convert_to_imperial=True
    ):
    """Main controller for running the drainage/peak-flow calculator with geospatial data
    
    Arguments:
        inlets {point feature layer} -- point features representing 
            inlets/catchbasins (i.e., point at which peak flow is being assessed)
        flow_dir_raster {raster layer} -- flow direction raster, derived from 
            a user-corrected DEM for an entire study area
        slope_raster {raster layer} -- a slope raster, derived from an 
            *un-corrected* DEM for an entire study area
        cn_raster {raster layer} -- Curve Number raster, derived using 
            prep_cn_raster() tool
        precip_table_noaa {path to csv} -- preciptation table from NOAA (csv)
        output {path for new point feature class} -- output point features; this is 
            a copy of the original inlets, with peak flow calculations appended
    
    Keyword Arguments:
        pour_point_field {field name} -- <optional> name of field containing unique IDs for
            the inlets feature class. Uses the OID/FID/GUID field (default: {None})
        input_watershed_raster {raster layer} -- <optional> , pre-calculated watershed 
            raster for the study area. If used, the values in each catchment must 
            correspond to values in the *pour_point_field* for the *inlets* (default: {None})
        area_conv_factor {float} -- <optional>  (default: 0.00000009290304)
        output_catchments {path for new polygon feature class} -- <optional>  output polygon 
            features; this is a vectorized version of the delineated watershed(s), with peak flow 
            calculations appended (default: {None})

    Returns:
        a tuple of two paths (strings): [0] = path to the output points and, if 
            specified, [1] = path to the output_catchments

    """

    # -----------------------------------------------------
    # SET ENVIRONMENT VARIABLES
    
    msg('Setting environment parameters...', set_progressor_label=True)
    env_raster = Raster(flow_dir_raster)
    env.snapRaster = env_raster
    env.cellSize = (env_raster.meanCellHeight + env_raster.meanCellWidth) / 2.0
    env.extent = env_raster.extent
    # for i in ListEnvironments():
    #     msg("\t%-31s: %s" % (i, env[i]))

    # -----------------------------------------------------
    # DETERMINE UNITS OF INPUT DATASETS

    msg('Determing units of reference raster dataset...', set_progressor_label=True)
    # get the name of the linear unit from env_raster
    unit_name = env_raster.spatialReference.linearUnitName
    acf, lcf = None, None
    # attempt to auto-dectect unit names for use with the Pint package
    if unit_name:
        if 'foot'.upper() in unit_name.upper():
            acf = 1 * units.square_foot
            lcf = 1 * units.foot
            msg("...auto-detected 'feet' from the source data")
        elif 'meter'.upper() in unit_name.upper():
            acf = 1 * (units.meter ** 2)
            lcf = 1 * units.meter
            msg("...auto-detected 'meters' from the source data")
        else:
            msg("Could not determine conversion factor for '{0}'".format(unit_name))
    else:
        msg("Reference raster dataset has no spatial reference information.")
    if acf and lcf:
        # get correct conversion factor for casting units to that required by equations in calc.py
        area_conv_factor = acf.to(units.kilometer ** 2).magnitude #square kilometers
        length_conv_factor = lcf.to(units.meter).magnitude #meters
        msg("Area conversion factor: {0}".format(area_conv_factor))
        msg("Length conversion factor: {0}".format(length_conv_factor))

    # -----------------------------------------------------
    # READ IN THE PRECIP TABLE

    msg('Loading precipitation table...', set_progressor_label=True)
    precip_tab = precip_table_etl_noaa(precip_table=precip_table_noaa)
    precip_tab_1d = precip_tab[0]

    # -----------------------------------------------------
    # PREPARE THE INPUTS/POUR POINTS
    
    msg('Prepping inlets...', set_progressor_label=True)

    if isinstance(inlets, FeatureSet):
        msg("(reading from interactive selection)", set_progressor_label=True)
        print(inlets)
        inlets_fs = so("inlets_featurset")
        inlets.save(inlets_fs)
        inlets = inlets_fs

    CopyFeatures_management(
        in_features=inlets, 
        out_feature_class=output
    )
    inlets_copy = output

    if not pour_point_field:
        i = Describe(inlets)
        if i.hasOID:
            pour_point_field = i.OIDFieldName
        # AddGlobalIDs_management(in_datasets="Inlet_Move10")

    # -----------------------------------------------------
    # DELINEATE WATERSHEDS

    if not input_watershed_raster:
        msg('Delineating catchments from inlets...', set_progressor_label=True)
        catchment_results = catchment_delineation(
            inlets=inlets_copy,
            flow_direction_raster=flow_dir_raster,
            pour_point_field=pour_point_field
        )
        catchment_areas = catchment_results['catchments']
        msg("Analyzing Peak Flow for {0} inlet(s)".format(catchment_results['count']), set_progressor_label=True)
    else:
        catchment_areas = input_watershed_raster

    # -----------------------------------------------------
    # DERIVE CHARACTERISTICS FROM EACH CATCHMENT NEEDED TO CALCULATE PEAK FLOW
    # area, maximum flow length, average slope, average curve number

    msg('Deriving calculation parameters for catchments...', set_progressor_label=True)
    catchment_data, catchment_geom = derive_data_from_catchments(
        catchment_areas=catchment_areas,
        flow_direction_raster=flow_dir_raster,
        slope_raster=slope_raster,
        curve_number_raster=cn_raster,
        area_conv_factor=area_conv_factor,
        length_conv_factor=length_conv_factor,
        out_catchment_polygons=output_catchments
    )

    all_results = []

    # -----------------------------------------------------
    # CALCULATE PEAK FLOW FOR EACH CATCHMENT

    SetProgressor('step', 'Analyzing catchments', 0, len(catchment_data),1)
    for idx, each_catchment in enumerate(catchment_data):
        
        msg("\n-----\nAnalyzing {0}".format(each_catchment["id"]))
        for i in each_catchment.items():
            msg("\t%-12s: %s" % (i[0], i[1]))

        # -----------------------------------------------------
        # CALCULATE TIME OF CONCENTRATION (Tc)

        # calculate the t of c parameter for this catchment
        time_of_concentration = calculate_tc(
            max_flow_length=each_catchment['max_fl'], 
            mean_slope=each_catchment['avg_slope'],
        )

        # -----------------------------------------------------
        # CALCULATE PEAK FLOW FOR ALL PRECIP PERIODS        

        

        # with everything generate peak flow estimates for the catchment
        peak_flow_ests = calculate_peak_flow(
            catchment_area_sqkm=each_catchment['area_up'], 
            tc_hr=time_of_concentration,
            avg_cn=each_catchment['avg_cn'],
            precip_table=precip_tab_1d,
            uid=each_catchment['id'],
            qp_header=QP_HEADER
        )

        # -----------------------------------------------------
        # BUILD A RESULT OBJECT
        
        #extend the peak_flow_ests dict with the catchment params dict
        peak_flow_ests.update(each_catchment)
        # update with other metric(s) we've generated
        peak_flow_ests['tc_hr'] = time_of_concentration
        # add in the pour point ID field and value
        peak_flow_ests[pour_point_field] = each_catchment['id']

        # append that to the all_results list
        all_results.append(peak_flow_ests)

        SetProgressorPosition()
    
    ResetProgressor()

    # convert our sequence of Python dicts into a table
    results_table = etl.fromdicts(all_results)

    # -----------------------------------------------------
    # CONVERT OUTPUT UNITS TO IMPERIAL (by default)
    
    # run unit conversions from metric to imperial if convert_to_imperial
    if convert_to_imperial:
        results_table = etl\
            .convert(results_table, 'max_fl', lambda v: (v * units.meter).to(units.feet).magnitude)\
            .convert('area_up', lambda v: (v * (units.kilometer ** 2)).to(units.acre).magnitude)\
            .convert({i: lambda v: (v * units.meter ** 3 / units.second).to(units.feet ** 3 / units.second).magnitude for i in QP_HEADER})


    # that last .convert() handles conversion of all the peak flow per storm frequency values from cubic meters/second to cubic feet/second in one go :)

    # -----------------------------------------------------
    # SAVE TO DISK
    
    # save to a csv
    temp_csv = "{0}.csv".format(so("qp_results", "timestamp", "folder"))
    etl.tocsv(results_table, temp_csv)
    msg("Results csv saved: {0}".format(temp_csv))
    # load into a temporary table
    results_table = load_csv(temp_csv)

    # -----------------------------------------------------
    # JOIN RESULTS TO THE GEODATA

    # join that to a copy of the inlets
    msg("Saving results to pour points layer", set_progressor_label=True)
    
    esri_output_fields = ";".join(output_fields)

    JoinField_management(
        in_data=inlets_copy, 
        in_field=pour_point_field, 
        join_table=results_table, 
        join_field=pour_point_field,
        fields=esri_output_fields
    )
    msg("Output inlets (points) saved\n\t{0}".format(inlets_copy))
    if catchment_geom:
        msg("Saving results to catchment layer", set_progressor_label=True)
        JoinField_management(
            in_data=catchment_geom, 
            in_field='gridcode',
            join_table=inlets_copy, 
            join_field=pour_point_field,
            fields=esri_output_fields
        )
        msg("Output catchments (polygons) saved\n\t{0}".format(catchment_geom))
      
    ResetProgressor()
    
    return inlets_copy, catchment_geom


def additional_run(
    results_table_csv,
    another_noaa_precip_table,
    out_csv=None,
    pour_point_id_field="pid",
    uses_imperial=True
    # qp_header=['Y1','Y2','Y5','Y10','Y25','Y50','Y100','Y200','Y500','Y1000'],
    # analysis_fields=['avg_slope', 'avg_cn', 'tc_hr', 'area_up', 'max_fl']
    ):
    """takes the intermediate CSV generated by main, and runs another set of peak flow calcs on it.

    Use for running different climate scenarios without the need to delineate, calculate flow-length, etc.
    
    :param results_table_csv: [description]
    :type results_table_csv: [type]
    :param another_noaa_precip_table: [description]
    :type another_noaa_precip_table: [type]
    :param out_csv: [description], defaults to None
    :param out_csv: [type], optional
    :param uses_imperial: [description], defaults to True
    :param uses_imperial: bool, optional
    :param qp_header: [description], defaults to ['Y1','Y2','Y5','Y10','Y25','Y50','Y100','Y200','Y500','Y1000']
    :param qp_header: list, optional
    :param analysis_fields: [description], defaults to ['avg_slope', 'avg_cn', 'tc_hr', 'area_up', 'max_fl']
    :param analysis_fields: list, optional
    :return: [description]
    :rtype: [type]
    """

    precip_table = precip_table_etl_noaa(another_noaa_precip_table)

    r = etl\
        .fromcsv(results_table_csv)\
        .convert({f:float for f in OUTPUT_FIELDS})

    if uses_imperial:
        r = etl\
            .convert(r, 'max_fl', lambda v: (v * units.feet).to(units.meter).magnitude)\
            .convert('area_up', lambda v: (v * (units.acre)).to(units.kilometer ** 2).magnitude)

    def rowmapper(row):

        result = calculate_peak_flow(
            catchment_area_sqkm=row['area_up'],
            tc_hr=row['tc_hr'],
            avg_cn=row['avg_cn'],
            precip_table=precip_table[0],
        )
        out_row = OrderedDict({f: row[f] for f in row.flds})
        out_row.update(result)
        return out_row.values()

    out_fields = [i for i in OUTPUT_FIELDS]
    out_fields.append(pour_point_id_field)

    r2 = etl\
        .rowmap(r, rowmapper, header=out_fields, failonerror=True)\
        .convert({f:float for f in QP_HEADER})\
        .convert({f:float for f in ANALYSIS_FIELDS})\
        .cut(*out_fields)

    if uses_imperial:
        r2 = etl.convert(
            r2,
            {i: lambda v: (v * units.meter ** 3 / units.second).to(units.feet ** 3 / units.second).magnitude for i in QP_HEADER}
        )

    if out_csv:
        etl.tocsv(r2, out_csv)

    return r2