'''
utils.py 

Some utilities
'''

import os, time

from arcpy import AddMessage, AddWarning, AddError, CreateUniqueName
from arcpy import env

import click

def msg(text, arc_status=None):
    """
    output messages through Click.echo (cross-platform shell printing) 
    and the ArcPy GP messaging interface
    """
    click.echo(text)
    if arc_status == "warning":
        AddWarning(text)
    elif arc_status == "error":
        AddError(text)
    else:
        AddMessage(text)

def so(prefix, suffix="random", where="fgdb"):
    """complete path generator for Scratch Output (for use with ArcPy GP tools)

    Generates a string represnting a complete and unique file path, which is
    useful to have for setting as the output parameters for ArcPy functions,
    especially those for intermediate data.

    Inputs:
        prefix: a string for a temporary file name, prepended to suffix
        suffix: unique value type that will be used to make the name unique:
            "u": filename using arcpy.CreateUniqueName(),
            "t": uses local time,
            "r": uses a hash of local time
            "<user string>": any other value provided will be used directly
        where: a string that dictates which available workspace will be
            utilized:
            "fgdb": ArcGIS scratch file geodatabase. this is the default
            "folder": ArcGIS scratch file folder. use sparingly
            "in_memory": the ArcGIS in-memory workspace. good for big
                datasets, but not too big. only set to this for intermediate
                data, as the workspace is not persistent.
                
    Returns:
        A string representing a complete and unique file path.

    """
    
    # set workspace location
    if where == "in_memory":
        location = "in_memory"
    elif where == "fgdb":
        location = env.scratchGDB
    elif where == "folder":
        location = env.scratchFolder
    else:
        location = env.scratchGDB
    
    # create and return full path
    if suffix == "unique":
        return CreateUniqueName(prefix, location)
    elif suffix == "random":
        return os.path.join(
            location,
            "{0}_{1}".format(
                prefix,
                abs(hash(time.strftime("%Y%m%d%H%M%S", time.localtime())))
            )
        )
    elif suffix == "timestamp":
        return os.path.join(
            location,
            "{0}_{1}".format(
                prefix,
                time.strftime("%Y%m%d%H%M%S", time.localtime())
            )
        )
    else:
        return os.path.join(location,"{0}_{1}".format(prefix,suffix))