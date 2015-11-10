#!/usr/bin/env python3

import requests
import sys
import xml.etree.ElementTree as ET

with open(sys.argv[1], 'r') as infile, open(sys.argv[2], 'w') as outfile:
    for pid in infile:
        url = "http://fedora.lib.umd.edu/fedora/get/{0}/umdm".format(pid.rstrip('\n'))
        print(url)
        response = requests.get(url)
        
        root = ET.fromstring(response.text)

        # Main title -> descMeta/title@type="main"/
        title = root.find('./title/[@type="main"]')
        print(title.text)

        # Summary -> descMeta/description@type="summary"/
        
        
        
# Coverage dates
# descMeta/covTime/date/

# <covTime>
# <century certainty="exact" era="ad">1801-1900</century>
# <date certainty="exact" era="ad">1834-09-1</date>
# </covTime>

# Repository
# descMeta/repository/corpname

# Archival Collection
# descMeta/realationships/relation@label="archivalcollection"/bibRef/title@type="main"/

# <relationships>
# <relation label="archivalcollection" type="isPartOf">
# <bibRef>
# <title type="main">Joseph Raynes papers</title>
# <bibScope type="series">1</bibScope>
# <bibScope type="box">1</bibScope>
# <bibScope type="folder">1</bibScope>
# <bibScope type="item">4</bibScope>
# </bibRef>
# </relation>
# </relationships>




     
#     else:
#         print("Downloading {0} ...".format(pid))
#         
#         response = requests.get(url, stream=True)
#         with open(outfile, 'wb') as of:
#             shutil.copyfileobj(response.raw, of)
#         del response
#         sleep(3)
