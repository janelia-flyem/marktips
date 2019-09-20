"""

marktips.py

see README.md for usage


"""

# ------------------------- imports -------------------------
# std lib
import argparse
from contextlib import contextmanager, redirect_stdout, redirect_stderr
import getpass
from io import StringIO
import json
import sys
import time


# third party
import requests

try:
    import dvidtools as dt
    hasDVIDtools = True
except ImportError:
    hasDVIDtools = False

# local
from . import __version__


# ------------------------- constants -------------------------
appname = "marktips.py"

todocomment = "placed by marktips.py v" + __version__

todoinstancename = "segmentation_todo"

# format = '2019-09-11 10:38:32'
timeformat = "%Y-%m-%d %H:%M:%S"


# ------------------------- code -------------------------

@contextmanager
def noredirect():
    # dummy context manager
    yield None


def postdvid(call, username, data):
    """
    POSTs the input data to DVID

    input: the URL to call; username; the data to be posted
    """
    call = addappuser(call, username)
    return requests.post(call, data=json.dumps(data))


def getdvid(call, username):
    """
    does a GET call to DVID

    input: URL to call; username
    output: requests response object
    """
    call = addappuser(call, username)
    return requests.get(call)


def addappuser(call, username):
    """
    add the user and app name to a call
    """
    if "u=" in call:
        # already has user; assume it has app, too
        return call

    if "?" not in call:
        call += "?"
    else:
        call += "&"
    call += "u={}&app={}".format(username, appname)
    return call


def getdefaultoutput():
    return {
        "version": __version__,
        "parameters": {
            "username": getpass.getuser(),
            "time": time.strftime(timeformat),
        },
    }


def errorquit(message):
    result = getdefaultoutput()
    result["status"] =  False
    result["message"] = message
    print(json.dumps(result))
    sys.exit(1)


class TipDetector:
    def __init__(self, serverport, uuid, bodyid, todoinstance, username=None,
        roi=None, excluded_roi=None):
        self.serverport = serverport
        self.uuid = uuid
        self.bodyid = bodyid
        self.todoinstance = todoinstance
        self.roi = roi
        self.excluded_roi = excluded_roi
        if username is None:
            self.username = getpass.getuser()
        else:
            self.username = username

        # hold description of what was run
        self.parameters = {
            # username = who is running this; todo-username = to whom the to do was assigned
            "username": getpass.getuser(),
            "todo-username": self.username,
            "time": time.strftime(timeformat),
        }

        self.locations = []
        self.nlocations = 0
        self.nlocationsroi = 0
        self.ntodosplaced = 0
        self.tplace = 0.0
        self.tfind = 0.0

        self.validateinput()

    def validateinput(self):
        # check body ID exists?  not so easy yet; we don't have the segmentation
        #   instance as input (we could), so we can't check; however,
        #   it does get caught by the "body doesn't have skeleton" check,
        #   which is true though a little misleading; for now, though,
        #   it's an adequate message

        # check RoIs exist
        if self.roi is not None and not self.RoIexists(self.roi):
            errorquit("RoI {} does not exist".format(self.roi))
        if self.excluded_roi is not None and not self.RoIexists(self.excluded_roi):
            errorquit("RoI {} does not exist".format(self.excluded_roi))

    def findandplace(self, find_only, show_progress, save_parameters):
        """
        find tips and place to do items; report results by printing json; quit

        input:  flag for finding tips but not placing to do;
                flag for showing progress bar on command line (in stderr)
                flag for storing run parameters on each to do
        """
        self.findtips(show_progress)
        if not find_only:
            self.placetodos(save_parameters)
        self.reportquit()

    def findtips(self, showprogress):
        """
        finds and stores tip locations for input body id
        """

        t1 = time.time()

        dt.set_param(self.serverport, self.uuid, self.username)

        # dt.detect_tips() sends output to stdout and stderr, which I want to control when
        #   I run from within NeuTu; however, the progress bar (which goes to stderr) is
        #   useful when run outside NeuTu; so trap and ignore stdout all the time, but
        #   if the user wants it, don't trap stderr so the progress bar is visible
        if showprogress:
            stderrRedirect = noredirect()
        else:
            stderrRedirect = redirect_stderr(StringIO())
        with stderrRedirect:
            with redirect_stdout(StringIO()):
                noskeleton = False
                try:
                    self.parameters["body ID"] = self.bodyid
                    tips = dt.detect_tips(self.bodyid)
                except ValueError as e:
                    if "appears to not have a skeleton" in e.__str__():
                        noskeleton = True
                    else:
                        raise e
        if noskeleton:
            errorquit("body " + self.bodyid + " does not appear to have a skeleton!")

        self.locations = tips.loc[:, ["x", "y", "z"]].values.tolist()
        self.nlocations = len(self.locations)

        # filter by RoI if applicable
        # must be inside this roi, if given:
        if self.roi is not None:
            self.parameters["RoI"] = self.roi
            insidelist = self.insideRoI(self.locations, self.roi)
            self.locations = [item for item, inside in zip(self.locations, insidelist) if inside]

        # must not be in this roi, if given:
        if self.excluded_roi is not None:
            self.parameters["excluded RoI"] = self.excluded_roi
            insidelist = self.insideRoI(self.locations, self.excluded_roi)
            self.locations = [item for item, inside in zip(self.locations, insidelist) if not inside]

        self.nlocationsroi = len(self.locations)

        t2 = time.time()
        self.tfind = t2 - t1

    def gettodos(self):
        """
        retrieve to do items on the body of interest
        """
        todocall = self.serverport + "/api/node/" + self.uuid + "/" + todoinstancename + "/label/" + self.bodyid
        r = getdvid(todocall, self.username)
        if r.status_code != requests.codes.ok:
            # bail out; later I'd prefer to have the error percolate up and be
            #   handled by the calling routine, but for now, just quit:
            message = "existing to do retrieval failed!\n"
            message += f"url: {todocall}\n"
            message += f"status code: {r.status_code}\n"
            message += f"returned text: {r.text}\n"
            errorquit(message)
        else:
            return r.json()

    def insideRoI(self, pointlist, roi):
        """
        input: list of [x, y, z] points
        output: list of [True, False, ...] indicating if each point is in self.roi
        """
        call = self.serverport + "/api/node/" + self.uuid + "/" + roi + "/ptquery"
        r = postdvid(call, self.username, data=pointlist)
        return r.json()

    def RoIexists(self, roi):
        call = self.serverport + "/api/node/" + self.uuid + "/" + roi + "/info"
        r = getdvid(call, self.username)
        return r.status_code == requests.codes.ok

    def placetodos(self, save_parameters):
        """
        posts a to do item at each previously found tip location

        input: flag whether to store run parameters on each to do
        """

        if len(self.locations) == 0:
            return

        t1 = time.time()

        # retrieve existing to do items on the body; if there is already a tip detection
        #   to do at the location, skip it; if it's another kind of to do, slightly offset
        #   the new tip detection to do so they coexist; keep in mind that the previous
        #   tip detection to do may also be offset and still need to be skipped!
        existingtodos = {tuple(td["Pos"]): td for td in self.gettodos()}

        # two passes through candidate locations; first, check for existing to do at
        #   the locations, and adjust locations as needed; then strip out Nones (meaning
        #   already a tip detection to do at that location):
        self.locations = [self.findvalidtodolocation(tuple(loc), existingtodos) for loc in self.locations]
        self.locations = [loc for loc in self.locations if loc is not None]

        annlist = [self.maketodo(loc, save_parameters) for loc in self.locations]
        self.postannotations(annlist)

        t2 = time.time()
        self.tplace = t2 - t1

    def neighbors(self, location):
        """
        input: (x, y, z) location
        output: list of (x, y, z) locations that are one unit away on the cardinal axes
        """
        x0, y0, z0 = location
        return [
            (x0 + 1, y0, z0),
            (x0 - 1, y0, z0),
            (x0, y0 + 1, z0),
            (x0, y0 - 1, z0),
            (x0, y0, z0 + 1),
            (x0, y0, z0 - 1),
        ]

    def findvalidtodolocation(self, location, existingtodos):
        """
        find a valid location for a possible tip detection to do;
        if there's already a tip detection to do there, return None;
        if there's already some other kind of to do, perturb the
        location slightly and return that, checking for more to do
        along the way; raise exception if you can't find a spot close by

        input: tuple (x, y, z) location of potential to do;
            dictionary of (x, y, z) location: existing to do items
        output: (x, y, z) location of valid to do location or None
        """

        # is there already a to do at that location?  if it's a tip
        #   to do, return None (duplicate)
        if location in existingtodos:
            if self.istiptodo(existingtodos[location]):
                return None
            else:
                # check surrounding locations
                for loc in self.neighbors(location):
                    if loc not in existingtodos:
                        return loc
                    elif self.istiptodo(existingtodos[loc]):
                        return None
                # if you get here, couldn't find a suitable location; that really
                #   shouldn't happen, so let's make it an actual error:
                errorquit("Could not place to do at location {}; all neighboring points occupied!".format(location))
        else:
            # nothing there, it's OK
            return location

    def istiptodo(self, todo):
        # allow for the possibility that the to do doesn't have
        #   all properties
        prop = todo["Prop"]
        return (prop.get("action", "") == "tip detector" or
            "marktips.py" in prop.get("comment", ""))

    def maketodo(self, location, save_parameters):
        """
        input: [x, y, z] location; flag whether to save run parameters on to do
        output: json for a to do annotation at that location
        """
        ann = {
            "Kind": "Note",
            "Prop": {},
        }
        ann["Pos"] = list(location)
        ann["Prop"]["comment"] = todocomment
        ann["Prop"]["user"] = self.username
        ann["Prop"]["checked"] = "0"
        ann["Prop"]["action"] = "tip detector"
        if save_parameters:
            # have to stringify the json or DVID will cry
            ann["Prop"]["run parameters"] = json.dumps(self.parameters)
        ann["Tags"] = ["action:tip_detector"]
        return ann

    def postannotations(self, annlist):
        """
        posts the list of annotations to dvid

        input: list of json annotations
        """

        todocall = self.serverport + "/api/node/" + self.uuid + "/segmentation_todo/elements"
        r = postdvid(todocall, self.username, data=annlist)
        if r.status_code != requests.codes.ok:
            # bail out; later I'd prefer to have the error percolate up and be
            #   handled by the calling routine, but for now, just quit:
            message = "to do placement failed!\n"
            message += f"url: {todocall}\n"
            message += f"status code: {r.status_code}\n"
            message += f"returned text: {r.text}\n"
            errorquit(message)
        else:
            # successful
            self.ntodosplaced = len(annlist)

    def reportquit(self):
        message = f"{len(self.locations)} tips found in {self.tfind}s; {self.ntodosplaced} to do items placed in {self.tplace}s"
        result = getdefaultoutput()
        result["parameters"].update(self.parameters)
        result["status"] = True
        result["message"] = message
        result["tfind"] = self.tfind
        result["tplace"] = self.tplace
        result["ttotal"] = self.tfind + self.tplace
        result["nlocations"] = self.nlocations
        result["nlocationsRoI"] = self.nlocationsroi
        result["nplaced"] = self.ntodosplaced
        result["locations"] = self.locations
        print(json.dumps(result))
        sys.exit(0)


def main():
    if not hasDVIDtools:
        errorquit("could not import dvid_tools library")

    parser = argparse.ArgumentParser(description="find and mark tips on neurons")

    # required positional arguments
    parser.add_argument("serverport", help="server and port of DVID server")
    parser.add_argument("uuid", help="UUID of the DVID node")
    parser.add_argument("bodyid", help="body ID of the body to find tips on")
    parser.add_argument("todoinstance", help="DVID instance name where to do items are stored")

    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--find-only", action="store_true", help="find tips only; do not place to do items")
    parser.add_argument("--show-progress", action="store_true", help="show a progress bar while running")
    parser.add_argument("--save-parameters", action="store_true", help="store run parameters in each to do placed")

    parser.add_argument("--roi", help="specify an optional DVID RoI; to do items will only be placed in this RoI")
    parser.add_argument("--excluded-roi", help="specify an optional DVID RoI; to do items will not be placed in this RoI")
    parser.add_argument("--username", help="specify a username to assign the to do items to")

    args = parser.parse_args()
    if not args.serverport.startswith("http://"):
        args.serverport = "http://" + args.serverport

    detector = TipDetector(args.serverport, args.uuid, args.bodyid, args.todoinstance, args.username,
        args.roi, args.excluded_roi)
    detector.findandplace(args.find_only, args.show_progress, args.save_parameters)


# ------------------------- script starts here -------------------------
if __name__ == '__main__':
    main()
