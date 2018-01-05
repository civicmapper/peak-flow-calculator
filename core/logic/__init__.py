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

# standard library imports
import os

# dependencies
from arcpy import AddMessage, AddWarning, AddError, Describe
from arcpy import CopyFeatures_management, JoinField_management

# 3rd party dependencies
# (not included with Esri ArcMap; attempt to install when not available)
try:
    import petl as etl
except:
    print("This tool requires Python PETL (https://pypi.python.org/pypi/petl).\nIf you've previously installed it but are seeing this message, you may need to restart your python interpreter.")
    from pkg_resources import WorkingSet , DistributionNotFound
    working_set = WorkingSet()
    try:
        dep = working_set.require('petl>=1.1')
    except DistributionNotFound:
        print("...installing...")
        try:
            from setuptools.command.easy_install import main as install
            install(['petl>=1.1'])
        except:
            print("This tool was unable to find or install the required dependencies.")
            exit

try:
    import click
except:
    print("This tool requires Python Click (https://pypi.python.org/pypi/click).\nIf you've previously installed it but are seeing this message, you may need to restart your python interpreter.")
    from pkg_resources import WorkingSet , DistributionNotFound
    working_set = WorkingSet()
    try:
        dep = working_set.require('click>=6')
    except DistributionNotFound:
        print("...installing...")
        try:
            from setuptools.command.easy_install import main as install
            install(['click>=6'])
        except:
            print("This tool was unable to find or install the required dependencies.")
            exit

# application imports
from data_io import precip_table_etl_noaa
from gp import prep_cn_raster, load_csv, join_to_copy, derive_data_from_catchments, catchment_delineation
from calc import calculate_tc, calculate_peak_flow
from utils import so, msg

# -----------------------------------------------------------------------------
# Primary workflow
#

def main(inlets, flow_dir_raster, slope_raster, cn_raster, precip_table_noaa, output, output_catchments=None, pour_point_field=None, input_watershed_raster=None, area_conv_factor=0.00000009290304):
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

    msg('Loading precipitation table...')
    precip_tab = precip_table_etl_noaa(precip_table=precip_table_noaa)
    precip_tab_1d = precip_tab[0]

    
    msg('Prepping inlets...')
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

    if not input_watershed_raster:
        msg('Delineating catchments from inlets...')
        catchment_results = catchment_delineation(
            inlets=inlets_copy,
            flow_direction_raster=flow_dir_raster,
            pour_point_field=pour_point_field
        )
        catchment_areas = catchment_results['catchments']
    else:
        catchment_areas = input_watershed_raster

    msg('Deriving calculation parameters for catchments...')
    catchment_params = derive_data_from_catchments(
        catchment_areas=catchment_areas,
        flow_direction_raster=flow_dir_raster,
        slope_raster=slope_raster,
        curve_number_raster=cn_raster,
        area_conv_factor=area_conv_factor,
        out_catchment_polygons=output_catchments
    )

    all_results = []

    for each_catchment in catchment_params[0]:
        msg("analyzing {0}\n\t{1}".format(each_catchment["id"],each_catchment))

        # calculate the t of c parameter for this catchment
        time_of_concentration = calculate_tc(
            max_flow_length=each_catchment['max_fl'], 
            mean_slope=each_catchment['avg_slope'],
        )

        # with everything generate peak flow estimates for the catchment
        peak_flow_ests = calculate_peak_flow(
            catchment_area_sqkm=each_catchment['area_sqkm'], 
            tc_hr=time_of_concentration,
            avg_cn=each_catchment['avg_cn'],
            precip_table=precip_tab_1d,
            uid=each_catchment['id']
        )
        
        #extend the peak_flow_ests dict with the catchment params dict
        peak_flow_ests.update(each_catchment)
        # add in the pour point field and value
        peak_flow_ests[pour_point_field] = each_catchment['id']

        # append that to the all_results list
        all_results.append(peak_flow_ests)

    # convert our sequence of Python dicts into a table
    temp_csv = "{0}.csv".format(so("qp_results", "timestamp", "folder"))
    etl.tocsv(etl.fromdicts(all_results), temp_csv)
    msg("temporary table saved: {0}".format(temp_csv))
    # load into a temporary table
    results_table = load_csv(temp_csv)
    # join that to a copy of the inlets
    JoinField_management(
        in_data=inlets_copy, 
        in_field=pour_point_field, 
        join_table=results_table, 
        join_field=pour_point_field,
        fields="Y1;Y2;Y5;Y10;Y25;Y50;Y100;Y200;avg_slope;avg_cn;area_sqkm;max_fl"
    )
    msg("Output saved {0}".format(inlets_copy))  

    if catchment_params[1]:
        JoinField_management(
            in_data=catchment_params[1], 
            in_field='gridcode',
            join_table=results_table, 
            join_field=pour_point_field,
            fields="Y1;Y2;Y5;Y10;Y25;Y50;Y100;Y200;avg_slope;avg_cn;area_sqkm;max_fl"
        )
        msg("Output saved {0}".format(catchment_params[1]))
      
    return inlets_copy, catchment_params[1]
