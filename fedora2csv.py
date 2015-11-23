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


def write_file(data, filetype):
    filename = sys.argv[2] + "-" + filetype + ".csv"
    with open(filename, 'w') as outfile:
        fieldnames = set().union(*(d.keys() for d in data))
        dw = csv.DictWriter(outfile, fieldnames=fieldnames)
        dw.writeheader()
        for d in data:
            dw.writerow(d)


def get_type(pid):
    url = "http://fedora.lib.umd.edu/fedora/get/{0}/doInfo".format(pid)
    print(url)
    response = requests.get(url)
    doinfo = ET.fromstring(response.text)
    type = doinfo.find('{http://www.itd.umd.edu/fedora/doInfo}type')
    return type.text


def get_metadata(pid):
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
    result['dates'] = [d.text for d in dates] if dates is not None else ''

    # Repository Element
    repository = umdm.find('./repository/corpName')
    result['repository'] = repository.text if repository is not None else ''

    # Collection Element
    collection = umdm.find('./relationships/relation/bibRef/title')
    result['collection'] = collection.text if collection is not None else ''
    
    return result


def get_rels(pid):
    result = {}
    url = "http://fedora.lib.umd.edu/fedora/get/{0}/rels-mets".format(pid)
    ns = {'xmlns':'http://www.loc.gov/METS/', 'xlink':'http://www.w3.org/1999/xlink'}
    
    response = requests.get(url)
    mets = ET.fromstring(response.text)
    rels = mets.find('./xmlns:structMap/xmlns:div/[@ID="rels"]', ns)
    
    # Get the pids of all related items
    collections = rels.findall('./xmlns:div/[@ID="isMemberOfCollection"]/xmlns:fptr', ns)
    for c in collections:
        id = c.attrib['FILEID']
        result[id] = {'id': id, 'type': 'collection'}
    parts = rels.findall('./xmlns:div/[@ID="hasPart"]/xmlns:fptr', ns)
    for p in parts:
        id = p.attrib['FILEID']
        result[id] = {'id': id, 'type': 'image'}
    
    # Get the page attributes for each part
    pages = mets.findall('./xmlns:structMap/xmlns:div/[@ID="images"]/xmlns:div', ns)
    for p in pages:
        id = p.find('./xmlns:div/xmlns:fptr', ns).attrib['FILEID']
        result[id].update({'order': p.attrib['ORDER'], 'label': p.attrib['LABEL']})
    
    # Get the pids for each related item
    files = mets.findall('./xmlns:fileSec/xmlns:fileGrp/xmlns:file', ns)
    for f in files:
        pid = f.find('./xmlns:FLocat', ns).attrib['{http://www.w3.org/1999/xlink}href']
        result[f.attrib['ID']].update({'pid': pid})
    
    return [result[r] for r in result]


def main():
    pids = load_pids(sys.argv[1])
    collections = []
    items = []
    files = []
    
    for pid in pids:
        type = get_type(pid)
        
        if type == "UMD_COLLECTION":
            pass     
        
        elif type == "UMD_IMAGE":
            metadata = get_metadata(pid)
            metadata['files'] = []
            relationships = get_rels(pid)

            for rel in relationships:
                if rel['type'] == 'collection':
                    collections.append(rel)
                elif rel['type'] == 'image':
                    url = 'http://fedora.lib.umd.edu/fedora/get/{0}/image'.format(
                        rel['pid'])
                    metadata['files'].append(url)
                    rel['url'] = url
                    files.append(rel)
                else:
                    print('unknown type "{0}"'.format(rel['type']))
            
            items.append(metadata)
            
        else:
            print('Unexpected digital object type {0}, skipping...'.format(type))
                    
    # save the items to file
    write_file(items, "items")
    
    # same the collections to file
    write_file(collections, "cols")
    
    # save the files to file
    write_file(files, "files")


if __name__ == "__main__":
    main()
