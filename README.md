# Culvert & Drainage Evaluation Models

This software is used for evaluating runoff during storm events over known drainages.

This project encompasses work originally developed by the [Cornell Soil & Water Lab](http://soilandwater.bee.cornell.edu/) (see Credits/Contributors, below). Enhancements and extensions are being developed by the teams at [CivicMapper](http://www.civicmapper.com) and [Spatial Analytix](http://www.spatialanalytixllc.com) in consultation with the Cornell Soil & Water Lab.

# Capabilities

In summary, this set of models will:

1. Determine the runoff peak discharge of given culvert's watershed using the SCS graphical curve number method.
2. Calculate the cross sectional area of each culvert and assign c and Y coefficients based on culvert characteristics
3. Determine the maximum capacity of a culvert using inlet control
4. Determine the maximum return period storm that the culvert can safely pass before overtopping for both current and future rainfall conditions.

## Inputs:

For each evaluation area (e.g., a county, a watershed, or other geography), the model requires:

1. Culvert Watershed data input: A CSV file containing data on culvert watershed characteristics including Culvert IDs, WS_area in sq km, Tc in hrs and CN
2. NRCC export CSV file of precipitation data (in) for the 1, 2, 5, 10, 25, 50, 100, 200 and 500 yr 24-hr storm events. Check that the precipitation from the 1-yr, 24 hr storm event is in cell K-11
3. Field data collection input: A CSV file containing culvert data gathered in the field using either then NAACC data colleciton format or Tompkins county Fulcrum app

## Outputs:

The model produces five intermediate and one final output table:

1. Culvert geometry file: A CSV file containing culvert dimensions and assigned c and Y coefficients
2. Capacity output: A CSV file containing the maximum capacity of each culvert under inlet control
3. Current Runoff output: A CSV file containing the peak discharge for each culvert's watershed for the analyzed return period storms under current rainfall conditions
4. Future Runoff output: A CSV file containing the peak discharge for each culvert's watershed for the analyzed return period storms under 2050 projected rainfall conditions
5. Return periods output: A CSV file containing the maximum return period that each culvert can safely pass under current rainfall conditions and 2050 projections.
6. Final Model ouptut: A CSV file that summarizes the above model outputs in one table
    
# Installation and Usage

This project relies upon the Python [Click](http://click.pocoo.org/) package for a simple, cross-platform, command line-based interface to the models.

(TBC)

# Contributions

(TBC)

## Development

(TBC)

---
# Credits/Contributors

* These scripts are based on the culvert evaluation model developed by Rebecca Marjerison in 2013
* David Gold, python script development, August 4, 2015
* Object-oriented structure and resiliency updates built by Noah Warnke, August 31 2016 (no formulas changed).
* Updated by Zoya Kaufmann June 2016 - August 2017
* Merged with older versions by Tanvi Naidu June 19 2017