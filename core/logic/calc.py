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

from utils import msg

def calculate_tc(
    max_flow_length, #units of meters
    mean_slope, 
    const_a=0.000325, 
    const_b=0.77, 
    const_c=-0.385
):
    """
    calculate time of concentration (hourly)

    Inputs:
        - max_flow_length: maximum flow length of a catchment area, derived
            from the DEM for the catchment area.
        - mean_slope: average slope, from the DEM *for just the catchment area*

    Outputs:
        tc_hr: time of concentration (hourly)
    """
    tc_hr = const_a * math.pow(max_flow_length, const_b) * math.pow((mean_slope / 100), const_c)
    return tc_hr

def calculate_peak_flow(
    catchment_area_sqkm, 
    tc_hr, 
    avg_cn, 
    precip_table, 
    uid=None,
    qp_header =['Y1','Y2','Y5','Y10','Y25','Y50','Y100','Y200']#,'Y500']
    ):
    """
    calculate peak runoff statistics at a "pour point" (e.g., a stormwater
    inlet, a culvert, or otherwise a basin's outlet of some sort) using
    parameters dervied from prior analysis of that pour point's catchment area
    (i.e., it's watershed or contributing area) and precipitation estimates.
    
    Inputs:
        - catchment_area_sqkm: area measurement of catchment in *square kilometers*
        - tc_hr: hourly time of concentration number for the catchment area
        - avg_cn: average curve number for the catchment area
        - precip_table: a precipitation frequency estimates "table" as a Numpy
        Array, derived from standard NOAA Preciptation Frequency Estimates
        tables (the `precip_table_etl()` function can automatically prep this)
    
    Outputs:
        - runoff: a dictionary indicating peak runoff at the pour point for
        various storm events by duration and frequency
    """
    
    # reference some variables:
    # time of concentration in hours
    tc = tc_hr
    # average curve number, area-weighted
    cn = avg_cn
    
    # Skip calculation altogether if curve number or time of concentration are 0.
    # (this indicates invalid data)
    if cn in [0,'',None] or tc in [0,'',None]:
        qp_data = [0 for i in range(0,len(qp_header))]#,Qp[8]]
        return OrderedDict(zip(qp_header,qp_data))
    
    # array for storing peak flows
    Qp = []
    
    # calculate storage, S in cm
    # NOTE: DOES THIS ASSUME CURVE NUMBER RASTER IS IN METERS?
    Storage = 0.1*((25400.0/cn)-254.0) #cn is the average curve number of the catchment area
    msg("\tStorage: {0}".format(Storage))
    Ia = 0.2*Storage #inital abstraction, amount of precip that never has a chance to become runoff
    msg("\tIa: {0}".format(Ia))
    #setup precip list for the correct watershed from dictionary
    P = numpy.array(precip_table)
    msg("\tP: {0}".format(P))
    #calculate depth of runoff from each storm
    #if P < Ia NO runoff is produced
    Pe = (P - Ia)
    Pe = numpy.array([0 if i < 0 else i for i in Pe]) # get rid of negative Pe's
    msg("\tPe: {0}".format(Pe))
    Q = (Pe**2)/(P+(Storage-Ia))
    msg("\tQ: {0}".format(Q))
    
    #calculate q_peak, cubic meters per second
    # q_u is an adjustment because these watersheds are very small. It is a function of tc,
    #  and constants Const0, Const1, and Const2 which are in turn functions of Ia/P (rain_ratio) and rainfall type
    #  We are using rainfall Type II because that is applicable to most of New York State
    #  rain_ratio is a vector with one element per input return period
    rain_ratio = Ia/P
    rain_ratio = numpy.array([.1 if i < .1 else .5 if i > .5 else i for i in rain_ratio])
    msg("\tRain Ratio: {0}".format(rain_ratio))
    # keep rain ratio within limits set by TR55

    Const0 = (rain_ratio ** 2) * -2.2349 + (rain_ratio * 0.4759) + 2.5273
    Const1 = (rain_ratio ** 2) * 1.5555 - (rain_ratio * 0.7081) - 0.5584
    Const2 = (rain_ratio ** 2)* 0.6041 + (rain_ratio * 0.0437) - 0.1761

    qu = 10 ** (Const0+Const1*numpy.log10(tc)+Const2*(numpy.log10(tc))**2-2.366)
    msg("\tqu: {0}".format(qu))
    q_peak = Q*qu*catchment_area_sqkm #qu has weird units which take care of the difference between Q in cm and area in km2
    msg("\tq_peak: {0}".format(q_peak))
    Qp = q_peak

    # TODO: parameterize the range of values (goes all the way back to how NOAA csv is ingested)
    qp_header = ['Y1','Y2','Y5','Y10','Y25','Y50','Y100','Y200']#,'Y500']
    qp_data = [Qp[0],Qp[1],Qp[2],Qp[3],Qp[4],Qp[5],Qp[6],Qp[7]]#,Qp[8]]

    results = OrderedDict(zip(qp_header,qp_data))
    msg("Results:")
    for i in results.items():
        msg("\t%-5s: %s" % (i[0], i[1]))

    return results
