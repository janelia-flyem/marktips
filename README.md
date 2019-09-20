# marktips

"marktips.py" is a Python script that will find tips of neurons that should be reviewed and place a to do item on each one in DVID. Neurons must have a skeleton available in DVID in order to use the script. This script relies on the [dvid_tools](https://github.com/flyconnectome/dvid_tools) library for the actual tip detection.

# installation

This script requires the "requests" library and the "dvid_tools" library.

Install the most recent tagged commit from GitHub.  

# usage

The script can be run stand-alone or from within the [NeuTu](https://github.com/janelia-flyem/NeuTu) application. In NeuTu, right-click on a body and choose "Tip Detection dialog..." to run the script from the GUI.

usage:

```
python marktips.py serverport uuid bodyid todoinstance


serverport = server and port of DVID instanc
uuid = UUID of data
bodyid = ID of the body to find tips for
todoinstance = name of data instance in DVID that will hold the to do items

optional flags:

--version prints the version and quits
--find-only finds and returns the tip locations but does not place the to do items
--roi (RoI name) discards any found tips that are not within the input DVID RoI
--excluded-roi (RoI name) discards any found tips that are within the input DVID RoI
    NOTE: Be careful if using both RoI options together!  It's possible to exclude all tips.
--show-progress enables display of a progress bar while tips are detected (in stderr); as a side-effect, other warnings will also be shown
--username (username) assigns the to do items to the input username rather than the user running the script
```

When the script is finished running, it will print a json object to the screen with the following data:

```
    {
    "status": true or false (success or failure)
    "message": error or success message
    "version": version of marktips 

    # when successful, more data will be provided:

    "parameters": dictionary with run parameters
        # should always include:
        "username": username running the script
        "time": time stamp when script was started, in format '2019-09-09 10:38:32'

        # may include, when successful:
        "todo-username": username that the to do items were assigned to
        "body ID": the ID of the body
        "RoI": the RoI where the to do items were placed
        "excluded RoI": the RoI where to do items were not allowed to be placed

    "tfind": time in seconds taken to find tips
    "tplace": time in seconds to place to do items
    "ttotal": tfind + tplace

    "locations": list of [x, y, z] locations of the tips in the RoI
    "nlocations": number of tips found
    "nlocationsRoI": number of tips found in the input RoI
    "nplaced": number of to do items placed; if nplaced < nlocations, it indicates that some locations already had to do items (which were not replaced), or some items were not placed due to RoI restrictions
    }
```

# version history

The version history for marktips.py can be found [on the wiki](https://github.com/janelia-flyem/marktips/wiki/Version-history).