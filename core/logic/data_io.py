"""

io.py

functions for managing file input/output and extract/transform/load routines

"""

# standard library
import csv
# dependencies (numpy included with ArcPy)
import numpy
# dependencies (3rd party)
import petl as etl

def precip_table_etl_cnrccep(
    ws_precip,
    rainfall_adjustment=1
    ):
    """
    Extract, Transform, and Load data from a Cornell Northeast Regional
    Climate Center Extreme Precipitation estimates csv into an array
    
    Output: 1D array containing 24-hour duration estimate for frequencies 1,2,5,10,25,50,100,200 years. Example: 
        [5.207, 6.096, 7.5438, 8.8646, 10.9982, 12.9286, 15.2146, 17.907, 22.1996]
    
    """
    precips = []

    # Open the precipitation data csv and read all the precipitations out.
    with open(ws_precip) as g:
        input_precip= csv.reader(g)
        
        # Skip the first 10 rows of the csv, which are assorted header information.
        for j in range (1, 11):
            next(g)

        k=1
        for row in input_precip:
            # Grab data from column containing 24-hour estimate
            P=float(row[10])
            # convert to cm and adjust for future rainfall conditions (if rainfall_adjustment is > 1)
            precips.append(P*2.54*rainfall_adjustment)
            if k>8:
                break
            else:
                k=k+1
    return precips

def precip_table_etl_noaa(
    precip_table,
    rainfall_adjustment=1,
    frequency_min=1,
    frequency_max=1000,
    conversion_factor=2.54,
    desc_field="by duration for ARI (years):",
    duration_val="24-hr:"
    ):
    """
    Extract, Transform, and Load data from a NOAA PRECIPITATION FREQUENCY
    ESTIMATES matrix (in a csv) into an array used by the runoff calculator.
    
    Required Inputs:
        - precip_table: NOAA PRECIPITATION FREQUENCY ESTIMATES csv, in inches.
    Optional Inputs:
        - rainfall_adjustment: multipler to adjust for future rainfall
            conditions. defaults to 1.
        - frequency_min: the min. annual frequency to be returned. Default: 1
        - frequency_max: the max. annual frequency to be returned. Default: 1000
        - conversion_factor: apply to rainfall values. Default: 2.54
            (convert inches to centimeters).
        - desc_field: exact field name from NOAA table in first column.
            Defaults to "by duration for ARI (years):". Used for selecting
            data.
        - duration_val: exact row value in the desc_field from NOAA table that
            contains the duration of interest. Defaults to "24-hr:". Used for
            selecting data.
    Outputs:
        - precip_array: 1D array containing 24-hour duration estimate for
        frequencies 1,2,5,10,25,50,100,200,500,and 1000 year storm events
    """
    # load the csv table, skip the file header information, extract rows we need
    t1 = etl\
        .fromcsv(precip_table)\
        .skip(13)\
        .rowslice(0,19)
    # grab raw data from the row containing the x-hour duration event info
    t2 = etl\
        .select(t1, desc_field, lambda v: v == duration_val)\
        .cutout(desc_field)
    # generate a new header with only columns within frequency min/max
    h = tuple([
        i for i in list(etl.header(t2)) if (int(i) >= frequency_min and int(i) <= frequency_max)
    ])
    # for events within freq range, convert to cm, adjust for future rainfall
    t3 = etl\
        .cut(t2, h)\
        .convertall(lambda v: round(float(v) * conversion_factor * rainfall_adjustment, 2))
    # convert to a 1D array (values cast to floats)
    precips = list(etl.data(t3)[0])
    # also convert to a dictionary, for lookup by event
    precips_lookup = list(etl.dicts(t3))[0]
    # return 1D array and dictionary
    return precips, precips_lookup
