# marktips

"marktips.py" is a Python script that will find tips of neurons that should be reviewed and place a to do item on each one in DVID. Neurons must have a skeleton available in DVID in order to use the script. This script relies on dvid_tools for the actual tip detection.

In general, the script is designed to be used from within NeuTu (support to be released soon). However, it can be run stand-alone if needed.

usage:

python marktips.py serverport uuid bodyid todoinstance

serverport = server and port of DVID instanc
uuid = UUID of data
bodyid = ID of the body to find tips for
todoinstance = name of data instance in DVID that will hold the to do items

When the script runs, you will see a text-based progress bar showing its progress (courtesy of dvid_tools). After it's done, it will print a json object to the screen with the following data:

```
    {
    "status": true or false (success or failure)
    "message": error or success message

    # when successful, more data will be provided:
    "tfind": time in seconds taken to find tips
    "tplace": time in seconds to place to do items
    "ttotal": tfind + tplace

    "locations": list of [x, y, z] locations of the tips
    "nlocations": number of locations
    }
```

# requirements

This script requires the "requests" library and the "dvid_tools" library.