# Peak Flow Calculator

This software is used for calculating peak flow at given points (typically, inlets/catch basins) over a hydrologically-corrected DEM

This project encompasses work originally developed by the [Cornell Soil & Water Lab](http://soilandwater.bee.cornell.edu/) (see Credits/Contributors, below). The CLI and ArcGIS toolbox adaptation are by the teams at [CivicMapper](http://www.civicmapper.com) and [Spatial Analytix](http://www.spatialanalytixllc.com).

# Capabilities

In summary, this toolset will determine the runoff peak discharge of given point's watershed using the SCS graphical curve number method.

## Inputs:

(TBC)

## Outputs:

(TBC)
    
# Installation

*...when the only time you interact with Python is tangentialy through ArcMap*

Since this calculator requires some third party libraries available on [`pypi`](https://pypi.python.org/pypi) as well as [`arcpy`](http://desktop.arcgis.com/en/arcmap/latest/analyze/arcpy/what-is-arcpy-.htm) (not available on [`pypi`](https://pypi.python.org/pypi)`), we need to install those dependencies in ArcMap's python installation. This shouldn't be a big deal, since ArcMap versions after 10.2 seem to configure the necessary environment variables for Python to work correctly for Windows.

1. Open up a command line interface. You can use `cmd.exe`.
    * Note: Powershell can get funky with Python virtual environments, which can make this more difficult than necessary. In general I highly recommend [cmder](http://cmder.net/) for a useful command line tool on Windows
1. run `cd C:\path\to\your\copy\of\peak-flow-calc` to put you into this folder. Running `dir` will list files in that directory; you should see `setup.py`.
1. run `python -m setup.py` to install the third party dependencies and register them with the Python installation that ArcMap uses. 
    * Depending on how Python was installed on your machine, the `python` portion of that command may or may not work (e.g., in some cases `python` gets taken by another Python installation). 
    * Since ArcMap uses Python 2.7.x, you may find that `py -2 -m setup.py` is what you need to run&mdash;that may be the case if you've gone and installed Python 3 using an official Python installer for Windows from [python.org](https://www.python.org/).
    * if you get an error that `python` can't be found/command is not recognized, then Python hasn't been set as an environment variable for Windows. See [this documentation](https://docs.python.org/2/using/windows.html#excursus-setting-environment-variables) for instructions on how to do that.

*note: in the future, when we start using ArcGIS Pro, we should be able to avoid this as that program and its version of `arcpy` use `conda`, a python package manager that works with `pypi`*

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
* CLI developed by Christian Gass @ CivicMapper, Fall 2017
* ArcGIS toolbox interface developed by Christian Gass @ CivicMapper, Fall 2017