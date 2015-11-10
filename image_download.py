#!/usr/bin/env python3

import shutil
import requests
import sys
import os
from time import sleep

pidfile = sys.argv[1]
outpath = sys.argv[2]

if not os.path.exists(outpath):
    os.makedirs(outpath)

with open(pidfile, 'r') as pf:
    pids = [p.rstrip('\n') for p in pf.readlines()]
    
print("Loaded {0} pids from {1}".format(len(pids), pidfile))

for pid in pids:
    outpid = pid.replace(':', '_', 1) + ".jpg"
    outfile = os.path.join(outpath, outpid)
    if os.path.exists(outfile):
        print("Skipping {0} because {1} already exists ...".format(pid, outfile))
    else:
        print("Downloading {0} ...".format(pid))
        url = "http://fedora.lib.umd.edu/fedora/get/{0}/image".format(pid)
        response = requests.get(url, stream=True)
        with open(outfile, 'wb') as of:
            shutil.copyfileobj(response.raw, of)
        del response
        sleep(3)
  
    
# "http://fedora.lib.umd.edu/fedora/get/{0}/umdm".format(pid)
