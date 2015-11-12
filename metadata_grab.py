#!/usr/bin/env python3

import csv
import requests
import sys
import xml.etree.ElementTree as ET
from time import sleep

def load_pids(infile):
    with open(infile, 'r') as f:
        result = [line.rstrip('\n') for line in f]
        return result

def write_csv(data):
    fieldnames = set().union(*(d.keys() for d in data))
    with open(sys.argv[2], 'w') as outfile:
        dw = csv.DictWriter(outfile, fieldnames=fieldnames)
        dw.writeheader()
        for d in data:
            dw.writerow(d)

def extract_type(pid):
    url = "http://fedora.lib.umd.edu/fedora/get/{0}/doInfo".format(pid)
    response = requests.get(url)
    doinfo = ET.fromstring(response.text)
    type = doinfo.find('{http://www.itd.umd.edu/fedora/doInfo}type')
    return type.text

def extract_metadata(pid):
    result = {'pid': pid}
    url = "http://fedora.lib.umd.edu/fedora/get/{0}/umdm".format(pid)
    response = requests.get(url)
    umdm = ET.fromstring(response.text)
    # Media Type
    mediatype = umdm.find('./mediaType/form')
    result['mediatype'] = mediatype.text if mediatype is not None else ''
    # Title Element
    title = umdm.find('./title/[@type="main"]')
    result['title'] = title.text if title is not None else ''
    # Summary Element
    summary = umdm.find('./description/[@type="summary"]')
    result['summary'] = summary.text if summary is not None else ''
    # Dates Elements
    dates = umdm.find('./covTime')
    result['dates'] = ";".join([d.text for d in dates]) if dates is not None else ''
    # Repository Element
    repository = umdm.find('./repository/corpName')
    result['repository'] = repository.text if repository is not None else ''
    # Collection Element
    collection = umdm.find('./relationships/relation/bibRef/title')
    result['collection'] = collection.text if collection is not None else ''
    return result

def main():
    pids = load_pids(sys.argv[1])
    result = []
    for pid in pids[:100]:
        if extract_type(pid) == "UMD_IMAGE":
            result.append(extract_metadata(pid))
    write_csv(result)

if __name__ == "__main__":
    main()

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
