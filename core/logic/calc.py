"""
calc.py

Core calculation logic for the runoff calculator. 

"""
import math
from collections import OrderedDict
# dependencies (numpy included with ArcPy)
import numpy
# dependencies (3rd party)
import petl as etl

from .utils import msg

QP_HEADER=['Y1','Y2','Y5','Y10','Y25','Y50','Y100','Y200','Y500','Y1000']

def calculate_tc(
    max_flow_length, #units of meters
    mean_slope, # percent slope
    const_a=0.000325,
    const_b=0.77,
    const_c=-0.385
    ):
    """
    calculate time of concentration (hourly)

    Inputs:
        - max_flow_length: maximum flow length of a catchment area, derived
            from the DEM for the catchment area.
        - mean_slope: average slope, from the DEM *for just the catchment area*. This must be
        percent slope, provided as an integer (e.g., 23, not 0.23)

    Outputs:
        tc_hr: time of concentration (hourly)
    """
    if not mean_slope:
        mean_slope = 0.00001
    tc_hr = const_a * math.pow(max_flow_length, const_b) * math.pow((mean_slope / 100), const_c)
    return tc_hr

def calculate_peak_flow(
    catchment_area_sqkm,
    tc_hr,
    avg_cn,
    precip_table,
    qp_header=QP_HEADER
    ):
    """Calculate peak runoff statistics at a "pour point" (e.g., a stormwater
    inlet, a culvert, or otherwise a basin's outlet of some sort) using
    parameters dervied from prior analysis of that pour point's catchment area
    (i.e., it's watershed or contributing area) and *24-hour* precipitation estimates.

    Note that the TR-55 methodology is designed around a 24-hour storm *duration*. YMMV
    if providing rainfall estimates (via the precip_table parameter) for other storm durations.
    
    This calculator by default returns peak flow for storm *frequencies* ranging from 1 to 1000 year events.
    
    Inputs:
        - catchment_area_sqkm: area measurement of catchment in *square kilometers*
        - tc_hr: hourly time of concentration number for the catchment area
        - avg_cn: average curve number for the catchment area
        - precip_table: precipitation estimates as a 1D array (a list)
        derived from standard NOAA Preciptation Frequency Estimates. Values in centimeters
        tables (the `precip_table_etl()` function can automatically prep this)
    
    Outputs:
        - runoff: a dictionary indicating peak runoff at the pour point for
        storm events by frequency
    """

    # reference some variables:
    # time of concentration in hours
    tc = tc_hr
    # average curve number, area-weighted
    cn = avg_cn
    
    # Skip calculation altogether if curve number or time of concentration are 0.
    # (this indicates invalid data)
    if cn in [0,'',None] or tc in [0,'',None]:
        qp_data = [0 for i in range(0,len(qp_header))]
        return OrderedDict(zip(qp_header, qp_data))
    
    # array for storing peak flows
    Qp = []
    
    # calculate storage, S in cm
    # NOTE: THIS ASSUMES THE CURVE NUMBER RASTER IS IN METERS
    Storage = 0.1 * ((25400.0 / cn) - 254.0) #cn is the average curve number of the catchment area
    #msg("Storage: {0}".format(Storage))
    Ia = 0.2 * Storage #inital abstraction, amount of precip that never has a chance to become runoff
    #msg("Ia: {0}".format(Ia))
    # setup precip list for the correct watershed from dictionary
    P = numpy.array(precip_table) #P in cm
    #msg("P: {0}".format(P))

    #calculate depth of runoff from each storm
    #if P < Ia NO runoff is produced
    Pe = (P - Ia)
    Pe = numpy.array([0 if i < 0 else i for i in Pe]) # get rid of negative Pe's
    #msg("Pe: {0}".format(Pe))
    Q = (Pe**2) / (P + (Storage - Ia))
    #msg("Q: {0}".format(Q))
    
    # calculate q_peak, cubic meters per second
    # q_u is an adjustment because these watersheds are very small. It is a function of tc,
    # and constants Const0, Const1, and Const2 which are in turn functions of Ia/P (rain_ratio) and rainfall type
    # We are using rainfall Type II because that is applicable to most of New York State
    # rain_ratio is a vector with one element per input return period
    rain_ratio = Ia/P
    rain_ratio = numpy.array([.1 if i < .1 else .5 if i > .5 else i for i in rain_ratio]) # keep rain ratio within limits set by TR55
    #msg("Rain Ratio: {0}".format(rain_ratio))

    # TODO: expose these as parameters; document here what they are (referencing the TR-55 documentation)
    # TODO: some of these are geographically-derived; use geodata to pull the correct/suggested ones in (possibly
    # in a function that precedes this)
    Const0 = (rain_ratio**2) * -2.2349 + (rain_ratio * 0.4759) + 2.5273
    Const1 = (rain_ratio**2) * 1.5555 - (rain_ratio * 0.7081) - 0.5584
    Const2 = (rain_ratio**2) * 0.6041 + (rain_ratio * 0.0437) - 0.1761

    #qu has weird units which take care of the difference between Q in cm and area in km2 (m^3 s^-1 km^-2 cm^-1)
    qu = 10 ** (Const0 + Const1 * numpy.log10(tc) + Const2 *  (numpy.log10(tc))**2 - 2.366)
    #msg("qu: {0}".format(qu))
    q_peak = Q * qu * catchment_area_sqkm # m^3 s^-1
    #msg("q_peak: {0}".format(q_peak.tolist()))

    # TODO: better parameterize the header here (goes all the way back to how NOAA csv is ingested)
    results = OrderedDict(zip(qp_header,q_peak))
    #msg("Results:")
    # for i in results.items():
        #msg("%-5s: %s" % (i[0], i[1]))

    return results

def peak_flow_core(
    mean_slope_pct,
    max_flow_length_m,
    rainfall_cm,
    basin_area_sqkm,
    avg_cn 
    ):
    """This is a bare bones version of the two functions above and represents 
    the core TR-55 logic originally developed by the Cornell Soil and Water lab. 
    
    Numbers go in, numbers come out.

    TODO: expose hardcoded constants as parameters, and document them.
    
    :param mean_slope_pct: average slope in the basin, as percent rise
    :type mean_slope_pct: float
    :param max_flow_length_m: maximum flow length, in meters
    :type max_flow_length_m: float
    :param rainfall_cm: rainfall for a 24 hour event, in centimeters
    :type rainfall_cm: float
    :param basin_area_sqkm: area of the basin, in square kilometers
    :type basin_area_sqkm: float
    :param avg_cn: average curve number of the basin, area-weighted
    :type avg_cn: float
    :return: peak flow, in cubic meters / second
    :rtype: float
    """

    # INIITAL CHECKS ------------------------------------------

    # Skip calculation altogether if curve number or time of concentration are 0.
    # (this indicates invalid data)
    if avg_cn in [0,'',None] or tc_hr in [0,'',None]:
        return None    

    # -------------------------------------------
    # TIME OF CONCENTRATION

    TC_CONST_A = 0.000325
    TC_CONST_B = 0.77
    TC_CONST_C = -0.385

    if not mean_slope_pct:
        mean_slope_pct = 0.00001

    # time of concentration in hours
    tc_hr = TC_CONST_A * math.pow(max_flow_length, TC_CONST_B) * math.pow((mean_slope_pct / 100), TC_CONST_C)
    
    # -------------------------------------------
    # STORAGE 
    
    # calculate storage, S in cm
    # NOTE: THIS ASSUMES THE CURVE NUMBER RASTER IS IN METERS
    storage = 0.1 * ((25400.0 / avg_cn) - 254.0)
    
    # inital abstraction, amount of precip that never has a chance to become runoff
    init_abstraction = 0.2 * storage 
    
    # -------------------------------------------
    # RUNOFF DEPTH 
    
    # calculate depth of runoff from each storm
    # if P < Ia NO runoff is produced
    Pe = (rainfall_cm - init_abstraction)
    if Pe < 0:
        return None

    Q = (Pe**2) / (rainfall_cm + (storage - init_abstraction))
    
    # -------------------------------------------
    # RAIN RATIO AND PEAK FLOW

    # calculate q_peak, cubic meters per second
    # q_u is an adjustment because these watersheds are very small. It is a function of tc,
    # and constants Const0, Const1, and Const2 which are in turn functions of Ia/P (rain_ratio) and rainfall type
    # We are using rainfall Type II because that is applicable to most of New York State
    # rain_ratio is a vector with one element per input return period
    rain_ratio = init_abstraction / P
    rain_ratio = [.1 if i < .1 else .5 if i > .5 else i for i in [rain_ratio]][0] # keep rain ratio within limits set by TR55
    
    CONST_0 = (rain_ratio**2) * -2.2349 + (rain_ratio * 0.4759) + 2.5273
    CONST_1 = (rain_ratio**2) * 1.5555 - (rain_ratio * 0.7081) - 0.5584
    CONST_2 = (rain_ratio**2) * 0.6041 + (rain_ratio * 0.0437) - 0.1761

    # qu has weird units which take care of the difference between Q in cm and area in km2 
    # qu is in m^3 s^-1 km^-2 cm^-1
    qu = 10 ** (CONST_0 + CONST_1 * numpy.log10(tc_hr) + CONST_2 *  (numpy.log10(tc_hr))**2 - 2.366)
    q_peak = Q * qu * catchment_area_sqkm # m^3 s^-1
    
    return q_peak