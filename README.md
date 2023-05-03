# Peak Flow Calculator (WIP)

This software is used for calculating peak flow at given points (typically, inlets/catch basins) over a hydrologically-corrected DEM.

This software encompasses work originally developed by the [Cornell Soil & Water Lab](http://soilandwater.bee.cornell.edu/) (on GitHub @ [github.com/SoilWaterLab](https://github.com/SoilWaterLab)). see *Credits/Contributors*, below.

This repository represents a hard fork of the Water Lab's [Culvert_Beta](https://github.com/SoilWaterLab/CulvertEvaluation) repository. Code from the original repository is limited primarily to equations found in `/core/logic/calc.py`.

## Capabilities

In summary, this toolset will determine the runoff peak discharge of given point's watershed using the SCS graphical curve number method. For more information on this method, see [Technical Release 55](https://www.nrcs.usda.gov/Internet/FSE_DOCUMENTS/stelprdb1044171.pdf).

## Installation

This toolbox relies on:

* the [ArcPy](https://pro.arcgis.com/en/pro-app/arcpy/get-started/what-is-arcpy-.htm) package in ArcGIS Pro
* [PETL](https://petl.readthedocs.io/en/stable/), a package for easily building data extract/transform/load workflows
* [Pint](https://pint.readthedocs.io), a package for working with units
* [Click](https://click.palletsprojects.com/en/7.x/), a package that helps provide a CLI for these tools
* [pytest](https://docs.pytest.org/en/latest/), for testing

As ArcGIS Pro is Windows-only software, this works only on Windows (see **Plans**, near the end of this Read Me)

There are a few ways to install. If you're unfamilar with Python Conda environments and plan on using this stricly within ArcGIS Pro, then start here:

### Installation with ArcGIS Pro

Download (or clone) the contents of this repository to your computer.

First, [start with these instructions for creating and activating an environment](https://pro.arcgis.com/en/pro-app/arcpy/get-started/what-is-conda.htm#ESRI_SECTION2_61E4CFA5BAC144659038854CADEFC625) on Esri's help site.

Then, move on to the instructions for [installing available packages](https://pro.arcgis.com/en/pro-app/arcpy/get-started/what-is-conda.htm#ESRI_SECTION2_85BC919097434B3B9AE1A746D793AA29).

Following those instructions, you'll need to install four packages:

* PETL
* Pint
* Click
* pytest

Once those are installed, make sure your new environment is active. You will likely need to restart ArcGIS Pro.

### Installation when you hanlde Conda yourself outside of ArcGIS Pro

(skip this if you installed per the instructions in the previous section)

* create a new Conda environment from the command line
* install packages from the included `requirements.txt` file to the environment.
* activate the environment in ArcGIS Pro

### Loading the toolbox

In your ArcGIS Pro project connect to a toolbox (follow [these instructions](https://pro.arcgis.com/en/pro-app/help/projects/connect-to-a-toolbox.htm) if you haven't done it before).

## Usage

The Peak Flow calculator takes several inputs:

* input point locations, representing locations at which peak flow is to be estimated
* a raster indicating flow direction
* a raster indicating slope (in percent)
* a raster indicating curve numbers calculated according the the TR-55 method. *At this time the curve number raster must use a CRS with meters for units.*
* a preciptation frequency estimates table from NOAA (`/sample_data/noaa_precip_table.csv` for the duration and frequencies expected by this tool)

From these, it calculates peak flow for every input point. Peak flow results are reported in cubic feet/second for every storm frequency from 1 to 1000 year storm.

### Via ArcGIS Pro

An ArcToolbox is provided for running these scripts in ArcGIS Pro, `PeakFlow.tbx`.

Two scripts are used to build and/or prep a curve number raster, which is a prerequisite for running the tool.

* *Build Curve Number Raster*: build a Curve Number Raster from scratch, using landcover, soils, and curve number lookup `CSV` file. A sample of the lookup table, which maps landcover class values to soil values and TR55 curve numbers, is available in `/sample_data/urbantreecanopy_curvenumber_lookup.csv`.
* *Prep Curve Number Raster*: if you already have a curve number raster from another source, this tool will snap and reproject it to a reference raster, which should be the DEM raster for the study area.

Three scripts run the Peak Flow Calculator:

* *Peak Flow Calculator*: the basic implementation of the peak flow calculator logic
* *Peak Flow Calculator - Interactive*: allows for pour points to be added interactively on the map, instead of from an existing layer
* *Peak Flow Calculator using Pre-Calc'd Basins*: same as the basic implementation, but allows the user to additionally provide a watershed basin raster as input

### Via CLI

You can run the toolbox outside of ArcGIS Pro from the command line, as long as ArcGIS Pro is installed/licensed on your machine.

*Currently*, the CLI exposes a few, slightly different versions of the tools described above:

* *Peak-Flow Calculator "Lite"*. Same as the basic implementation available in ArcToolbox tool above.
* *Peak-Flow Calculator "Full"*: an implementation of the peak flow calculator logic that automatically calculates flow direction and slope inputs from a DEM at run-time.
* *Prep Curve Number Raster*: Same as the ArcToolbox tool above.

Available commands will likely coorespond with available ArcToolbox tools in future iterations of this codebase.

## Development

* scripts in the `core/` root provide interfaces between the business logic contained in `core/logic/` and the ArcToolbox; Those suffixed by `_tbx` are referenced directly by tools in `PeakFlow.tbx`
* `core/logic/` contains the business logic. The `logic` module itself contains one function, `main`, which handles orchestrating the various underlying components end-to-end.
* `core/logic/calc.py` contains the equations used to calculate peak flow.
* `core/logic/data_io.py` is used for reading in preciption tables (and is where to park other custom data ingest routines)
* `core/logic/gp.py` contains all functions that perform geoprocessing using the ArcPy package, including reading and writing spatial datasets
* `core/logic/utils.py` contains utilty functions.

See the wiki for more information on the business logic.

## Plans

* We plan to develop a platform-agnostic version of this toolset that is not dependent on Esri licensing in the future.

## Credits/Contributors

* These scripts are based on the culvert evaluation model developed by Rebecca Marjerison at the Cornell Soil and Water Lab in 2013
* David Gold, python script development, August 4, 2015
* Object-oriented structure and resiliency updates built by Noah Warnke, August 31 2016 (no formulas changed).
* Updated by Zoya Kaufmann June 2016 - August 2017
* Merged with older versions by Tanvi Naidu June 19 2017
* Fork, refactor, and creation of CLI and ArcMap interfaces by Christian Gass @ CivicMapper, Fall 2017
* Updates for use within ArcGIS Pro by Christian Gass @ CivicMapper, Spring/Summer 2019
* Additional updates by Tal Cohen 2020
