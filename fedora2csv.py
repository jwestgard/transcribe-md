#!/usr/bin/env python3

import csv
import requests
import sys
import xml.etree.ElementTree as ET
from time import sleep


#= Function =========
# Load pids from file
#====================
def load_pids(infile):
    with open(infile, 'r') as f:
        result = [line.rstrip('\n') for line in f]
        return result


#= Function ==========
# write output to file
#=====================
def write_file(data, filetype):
    filename = sys.argv[2] + "-" + filetype + ".csv"
    with open(filename, 'w') as outfile:
        fieldnames = set().union(*(d.keys() for d in data))
        dw = csv.DictWriter(outfile, fieldnames=fieldnames)
        dw.writeheader()
        for d in data:
            dw.writerow({k:list_to_string(v, ";") for (k,v) in d.items()})


#= Function ========================
# convert lists to delimited strings
#===================================
def list_to_string(data, delimiter):
    if type(data) is list:
        return str(delimiter).join(data)
    else:
        return data
            

#= Function ========================
# get object type from Fedora server
#===================================
def get_type(pid):
    url = "http://fedora.lib.umd.edu/fedora/get/{0}/doInfo".format(pid)
    print(url)
    response = requests.get(url)
    doinfo = ET.fromstring(response.text)
    type = doinfo.find('{http://www.itd.umd.edu/fedora/doInfo}type')
    return type.text


#= Function ===================
# get metadata xml and parse it
#==============================
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
    if dates is None:
        result['century'] = ''
        result['date'] = ''
    else:
        for d in dates:
            result['century'] = [d.text for d in dates if d.tag == "century"]
            result['date'] = [d.text for d in dates if d.tag == "date"]

    # Repository Element
    repository = umdm.find('./repository/corpName')
    result['repository'] = repository.text if repository is not None else ''

    # Collection Element
    collection = umdm.find('./relationships/relation/bibRef/title')
    result['collection'] = collection.text if collection is not None else ''
    
    # Subject Elements
    subjects = umdm.findall('./subject/[@type="topical"]')
    result['subjects'] = [
        s.text for s in subjects if s is not ''] if subjects is not None else ''
    
    return result


#= Function ===========
# get handle for object
#======================
def get_handle(pid):
    suffix = "/umd-bdef:handle/getHandle/"
    url = "http://fedora.lib.umd.edu/fedora/get/{0}{1}".format(pid, suffix)
    response = requests.get(url)
    handle_xml = ET.fromstring(response.text)
    return handle_xml.find('./result/handlehttp').text


#= Function =========================
# prepare omeka CSVimport spreadsheet
#====================================
def prepare_csvimport(data):
    for d in data:
        import_version = {
            'Dublin Core:Identifier': [data['pid'], data['handle']],
            'Dublin Core:Type': data['mediatype'],
            'Dublin Core:Title': data['title'],
            'Dublin Core:Description': data['summary'],
            'Dublin Core:Date': data['date'],
            'Dublin Core:Temporal Coverage': data['century'],
            'Dublin Core:Extent': '{0} pages'.format(len(data['files'])),
            'Dublin Core:Relation': data['repository'],
            'Scripto:Status': 'To transcribe',
            'tags': data['subjects'],
            'recordType': 'Item',
            'collection': data['collection'],
            'file': data['files']
            }
    return import_version


#= Function ================================
# prepare omeka update spreadsheet for files
#===========================================
def prepare_omeka_files(data):
    for d in data:
        import_version = {
            'updateIdentifier': "Dublin Core:Title",
            'updateMode': 'Replace',
            'recordType': 'File',
            'recordIdentifier': data['url']
            }
    return import_version

#= Function ========================
# get related objects from rels-mets
#===================================
def get_rels(pid):
    result = {}
    url = "http://fedora.lib.umd.edu/fedora/get/{0}/rels-mets".format(pid)
    ns = {'xmlns':'http://www.loc.gov/METS/',
        'xlink':'http://www.w3.org/1999/xlink'}
    
    response = requests.get(url)
    mets = ET.fromstring(response.text)
    rels = mets.find('./xmlns:structMap/xmlns:div/[@ID="rels"]', ns)
    
    # Get the pids of all related items
    collections = rels.findall(
        './xmlns:div/[@ID="isMemberOfCollection"]/xmlns:fptr', ns)
    for c in collections:
        id = c.attrib['FILEID']
        result[id] = {'id': id, 'type': 'collection'}
    parts = rels.findall('./xmlns:div/[@ID="hasPart"]/xmlns:fptr', ns)
    for p in parts:
        id = p.attrib['FILEID']
        result[id] = {'id': id, 'type': 'image'}
    
    # Get the page attributes for each part
    pages = mets.findall(
        './xmlns:structMap/xmlns:div/[@ID="images"]/xmlns:div', ns)
    for p in pages:
        id = p.find('./xmlns:div/xmlns:fptr', ns).attrib['FILEID']
        result[id].update(
            {'order': p.attrib['ORDER'], 'label': p.attrib['LABEL']})
    
    # Get the pids for each related item
    files = mets.findall('./xmlns:fileSec/xmlns:fileGrp/xmlns:file', ns)
    for f in files:
        pid = f.find(
            './xmlns:FLocat', ns).attrib['{http://www.w3.org/1999/xlink}href']
        result[f.attrib['ID']].update({'pid': pid})
    
    return [result[r] for r in result]


#= Function ==================
# main loop to handle each pid
#=============================
def main():
    pids = load_pids(sys.argv[1])
    collections = {}
    items = []
    files = []
    
    # loop through the input pids
    for pid in pids:
        type = get_type(pid)
        
        if type == "UMD_COLLECTION":
            print('  => {0} is a collection; skipping...'.format(pid))
        
        elif type == "UMD_IMAGE":
            
            metadata = get_metadata(pid)
            relationships = get_rels(pid)
            metadata['handle'] = get_handle(pid)
            metadata['files'] = []
            metadata['has_part'] = []
            metadata['part_of'] = []
            
            # analyze relationships and assign object to appropriate list
            for rel in relationships:
                del rel['id']
                id = rel['pid']
                if rel['type'] == 'collection':
                    # if the collection is already in the list, append the pid
                    if id in collections:
                        collections[id]['children'].append(pid)
                    # otherwise, add the collection to main list
                    else:
                        rel['children'] = [pid]
                        collections[id] = rel
                    # add the collection pid to the item metadata
                    metadata['part_of'].append(id)
                        
                elif rel['type'] == 'image':
                    url = 'http://fedora.lib.umd.edu/fedora/get/{0}/image'.format(id)
                    metadata['files'].append(url)
                    metadata['has_part'].append(id)
                    rel['url'] = url
                    files.append(prepare_omeka_files(rel))
                    
                else:
                    print('unknown type "{0}"'.format(rel['type']))
            
            items.append(prepare_csvimport(metadata))
            
        else:
            print('Unexpected digital object type {0}, skipping...'.format(
                type))
                    
    # save the items to file
    write_file(items, "items")
    
    # convert collections dict to list and save to file
    collections_list = [collections[d] for d in collections]
    write_file(collections_list, "collections")
    
    # save the files to file
    write_file(files, "files")


#============
# main logic
#============
if __name__ == "__main__":
    main()
