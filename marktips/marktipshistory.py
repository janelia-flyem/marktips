"""

marktipshistory.py

this script examines a body's to do items to report when marktips.py has been
previously run on that body

see project wiki for usage


"""

# ------------------------------ imports ------------------------------
# std lib
import argparse
import collections
import getpass
import json
import sys

# third party
import requests

# local
from . import __version__

# someday factor these out into a library file, but
#   for now, grab from the other script:
from .marktips import getdvid, errorquit, getdefaultoutput


# ------------------------------ constants ------------------------------
appname = "marktipshistory.py"


# ------------------------------ code ------------------------------
class MarktipsHistoryFinder:
    def __init__(self, serverport, uuid, bodyid, todoinstance):
        self.serverport = serverport
        self.uuid = uuid
        self.bodyid = bodyid
        self.todoinstance = todoinstance

    def findhistory(self):

        todolist = self.gettodos()

        # sort through them
        # the timestamp should be enough to identify individual runs of marktips; we
        #   report time to the second, and it takes much longer than that; to be safe,
        #   though, key on time and body ID pair; we'll store the full run params
        #   from one such run, but we will assume that they all match if the time and
        #   body ID do, without checking
        params = {}
        counts = collections.Counter()
        for todo in todolist:
            props = todo["Prop"]
            if props["action"] != "tip detector" or "run parameters" not in props:
                # this will miss runs with marktips 0.2 or earlier
                continue
            todoparams = json.loads(props["run parameters"])
            key = todoparams["time"], todoparams["body ID"]
            if key not in params:
                params[key] = todoparams
            counts[key] += 1
        self.reportquit(params, counts)

    def reportquit(self, paramdict, paramcounts):
        """
        input: dict {(time, body ID): param dict}, {(time, body ID): count}
        output: none (prints json output to screen)
        """
        message = "marktipshistory ran successfully"
        result = getdefaultoutput()
        result["status"] = True
        result["message"] = message
        result["history"] = []

        for key, params in paramdict.items():
            # we only pass on a subset of all parameters
            temp = {}
            temp["time"] = params["time"]
            temp["body ID"] = params["body ID"]
            temp["RoI"] = params.get("RoI", "")
            temp["excluded RoI"] = params.get("excluded RoI", "")
            temp["count"] = paramcounts[key]
            result["history"].append(temp)

        print(json.dumps(result))
        sys.exit(0)

    def gettodos(self):
        """
        retrieve to do items on the body of interest
        """
        todocall = self.serverport + "/api/node/" + self.uuid + "/" + self.todoinstance + "/label/" + self.bodyid
        r = getdvid(todocall, getpass.getuser())
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


def main():
    parser = argparse.ArgumentParser(description="report history of marktips.py use")

    # positional
    parser.add_argument("serverport", help="server and port of DVID server")
    parser.add_argument("uuid", help="UUID of the DVID node")
    parser.add_argument("bodyid", help="body ID of the body to find tips on")
    parser.add_argument("todoinstance", help="DVID instance name where to do items are stored")

    parser.add_argument("--version", action="version", version=__version__)

    args = parser.parse_args()
    if not args.serverport.startswith("http://"):
        args.serverport = "http://" + args.serverport

    finder = MarktipsHistoryFinder(args.serverport, args.uuid, args.bodyid, args.todoinstance)
    finder.findhistory()


# ------------------------------ script starts here ------------------------------
if __name__ == "__main__":
    main()
