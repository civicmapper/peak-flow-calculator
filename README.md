# Peak Flow Calculator

This software is used for calculating peak flow at given points (typically, inlets/catch basins) over a hydrologically-corrected DEM.

This software encompasses work originally developed by the [Cornell Soil & Water Lab](http://soilandwater.bee.cornell.edu/) (on GitHub @ [github.com/SoilWaterLab](https://github.com/SoilWaterLab)). see *Credits/Contributors*, below. 

This repo represents a hard fork of the Water Lab's [CulvertBeta](https://github.com/SoilWaterLab/CulvertEvaluation) project.

## Capabilities

In summary, this toolset will determine the runoff peak discharge of given point's watershed using the SCS graphical curve number method. For more information on this method, see [Technical Release 55](https://www.nrcs.usda.gov/Internet/FSE_DOCUMENTS/stelprdb1044171.pdf).

## Installation

This toolbox relies on:

* the [ArcPy](https://pro.arcgis.com/en/pro-app/arcpy/get-started/what-is-arcpy-.htm) package in ArcGIS Pro
* [PETL](https://petl.readthedocs.io/en/stable/), a package for easily building data extract/transform/load workflows
* [Pint](https://pint.readthedocs.io), a package for working with units

(TBC)

## Development

(TBC)

## Credits/Contributors

* These scripts are based on the culvert evaluation model developed by Rebecca Marjerison at the Cornell Soil and Water Lab in 2013
* David Gold, python script development, August 4, 2015
* Object-oriented structure and resiliency updates built by Noah Warnke, August 31 2016 (no formulas changed).
* Updated by Zoya Kaufmann June 2016 - August 2017
* Merged with older versions by Tanvi Naidu June 19 2017
* Fork, refactor, and creation of CLI and ArcMap interfaces by Christian Gass @ CivicMapper, Fall 2017
* Updates for ArcGIS Pro by Christian Gass @ CivicMapper, Spring 2019