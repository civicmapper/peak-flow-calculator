ECHO "Cloning ArcGIS Pro Conda environment"
"C:\Program Files\ArcGIS\Pro\bin\Python\Scripts\conda.exe" create --name peakflowcalc --clone "c:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3"
ECHO "Activating peakflowcalc environment"
activate peakflowcalc
ECHO "Installing dependencies"
pip install petl pint click