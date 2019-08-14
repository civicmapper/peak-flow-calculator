# Set up ArcGIS Pro 

The Peak Flow toolbox relies on a few FOSS Python packages. You'll need to make sure these are available to ArcGIS Pro in order for

## Create a New Python environment in ArcGIS Pro

(This summarizes [these instructions for creating and activating an environment](https://pro.arcgis.com/en/pro-app/arcpy/get-started/what-is-conda.htm#ESRI_SECTION2_61E4CFA5BAC144659038854CADEFC625) on Esri's help site.)

1. Under `Project > Settings > Python`, click the `Manage Environments` button. A new window will open.
2. Click `Clone Default`. This will create a new Python environment. It make take some time. 
3. Once the environment is created, check it. You will see a message `Restart ArcGIS Pro for your environment changes to take effect.`
4. Select `OK` at the bottom of the new window.
5. Restart ArcGIS Pro. Once restarted, open up the manage environments dialog to confirm the Python environment has changed.

> *Note: if the environment fails to create, you may need to run ArcGIS Pro as with administrator privileges. Right click your ArcGIS Pro icon and select `Run as Adminstrator`.*

## Install Python packages required by the Peak Flow tool

(This summarizes the instructions for [installing available packages](https://pro.arcgis.com/en/pro-app/arcpy/get-started/what-is-conda.htm#ESRI_SECTION2_85BC919097434B3B9AE1A746D793AA29).

You'll need to install three additional Python packages in your environmentto use the tool.

* PETL
* Pint
* Click

1. Under `Project > Settings > Python`, confirm your Project Environment is set to the one you created above.
2. Select the `Add Packages` button.
3. In the text box that appears to the right, search for `Click`. This will bring up a list of python packages.
4. Select `Click`. To the right of the list will appear a description of the package with an `Install` button.
5. Select `Install`, agree to terms of use, and select Install.
6. Repeat steps 3-5 for the other two packages, `Pint` and `PETL`.

If you're developing the tool, additionally install `pytest` for automated testing support

# Troubleshooting

* environment fails to create: you may need to run ArcGIS Pro as with administrator privileges. Right click your ArcGIS Pro icon and select `Run as Adminstrator`.*
