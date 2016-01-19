#!/usr/bin/env python3
import argparse
import csv
import requests
import sys
from time import sleep
import xml.etree.ElementTree as ET


#= Function =========
# Load data from file
#====================
def load_file(infile):
    with open(infile, 'r') as f:
        result = [line.rstrip('\n') for line in f]
        return result


#= Function ==========
# write output to file
#=====================
def write_file(data, filename):
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
    # print(url)
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
    # print("umdm response: {0}".format(response))
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
    result['subjects'] = []
    subjects = umdm.findall('./subject/[@type="topical"]')
    for s in subjects:
        if not s.text.isspace():
            result['subjects'].append(s.text)
    
    return result


#= Function ==
# get handle
#=============
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
            'Dublin Core:Extent': '{0} pages'.format(len(data['file_urls'])),
            'Dublin Core:Relation': data['repository'],
            'Scripto:Status': 'To transcribe',
            'tags': data['subjects'],
            'recordType': 'Item',
            'collection': data['collection'],
            'file': data['file_urls']
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
            'recordIdentifier': data['label']
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
    
    # Get the pids of all related items, first the collections
    collections = rels.findall(
        './xmlns:div/[@ID="isMemberOfCollection"]/xmlns:fptr', ns)
    for c in collections:
        id = c.attrib['FILEID']
        result[id] = {'id': id, 'type': 'collection', 'rel': 'member of'}
        
    # Then get the parts of the object
    parts = rels.findall('./xmlns:div/[@ID="hasPart"]/xmlns:fptr', ns)
    for p in parts:
        id = p.attrib['FILEID']
        result[id] = {'id': id, 'type': 'image', 'rel': 'has part'}
    
    # Attach the page attributes (order and label) for each part
    pages = mets.findall(
        './xmlns:structMap/xmlns:div/[@ID="images"]/xmlns:div', ns)
    for p in pages:
        id = p.find('./xmlns:div/xmlns:fptr', ns).attrib['FILEID']
        result[id].update(
            {'order': p.attrib['ORDER'], 'label': p.attrib['LABEL']})
    
    # Attach the pid for each related item
    files = mets.findall('./xmlns:fileSec/xmlns:fileGrp/xmlns:file', ns)
    for f in files:
        pid = f.find(
            './xmlns:FLocat', ns).attrib['{http://www.w3.org/1999/xlink}href']
        result[f.attrib['ID']].update({'pid': pid})
    
    # convert the result dictionary to a list, dropping the file id
    return [result[r] for r in result if r is not 'id']


#= Function ==================
# main loop to handle each pid
#=============================
def main():
    collections = {}
    items = []
    files = []

    # parse arguments
    parser = argparse.ArgumentParser(
        description='Extract Fedora2 Objects and Load Elsewhere')
    parser.add_argument('--infile', '-i', action='store', 
        help='file containing identifiers of objects to be captured')
    parser.add_argument('--outfile', '-o', action='store', 
        help='path to outputfile (different suffixes will be supplied)')
    parser.add_argument('--resume', '-r', action='store_true')
    args = parser.parse_args()

    pids = load_file(args.infile)
    
    if args.resume:
        complete = load_file(outfile)
    
    filename = args.outfile + "-items.csv"
    with open(filename, 'w') as outfile:
        fieldnames = ['Dublin Core:Identifier', 'Dublin Core:Type', 
            'Dublin Core:Title', 'Dublin Core:Description', 'Dublin Core:Date',
            'Dublin Core:Temporal Coverage', 'Dublin Core:Extent', 
            'Dublin Core:Relation', 'Scripto:Status', 'tags', 'recordType', 
            'collection', 'file']
        dw = csv.DictWriter(outfile, fieldnames=fieldnames)
        dw.writeheader()
        # loop through the input pids
        for pid in pids:
            print(pid)
            type = get_type(pid)
            
            if type == "UMD_COLLECTION":
                print('  => {0} is a collection; skipping...'.format(pid))
        
            elif type == "UMD_IMAGE":
                metadata = get_metadata(pid)
                metadata['rels'] = get_rels(pid)
                metadata['handle'] = get_handle(pid)
                metadata['file_urls'] = []
                metadata['has_part'] = []
                metadata['is_part_of'] = []
            
                for rel in metadata['rels']:
                    if rel['type'] == 'collection':
                        # add the collection pid to the item metadata
                        metadata['is_part_of'].append(rel['pid'])
                        # if the collection is already in the list, append the pid
                        if rel['pid'] in collections:
                            collections[rel['pid']]['children'].append(pid)
                        # otherwise, add the collection to the collections list
                        else:
                            collections[rel['pid']] = {'children': [pid]}
 
                    elif rel['type'] == 'image':
                        url = 'http://fedora.lib.umd.edu/fedora/get/'
                        url += '{0}/image'.format(rel['pid'])
                        metadata['file_urls'].append(url)
                        metadata['has_part'].append(rel['pid'])
                        
                        # add page-level info to files list
                        page = rel
                        page['url'] = url
                        files.append(page)
                
                # add item-level info to items list
                items.append(metadata)
                row = prepare_csvimport(metadata)
                dw.writerow({k:list_to_string(v, ";") for (k,v) in row.items()})
                
            else:
                print('Unexpected digital object type {0}, skipping...'.format(
                    type))
    
    # construct arch_colls list based on collection metadata not fedora rels
    archival_collections = set([i['collection'] for i in items])
    archival_collections_list = []
    # populate dictionary for each collection with name and pids of members
    for a in archival_collections:
        item_dict = {'collection': a}
        item_dict['members'] = [i['pid'] for i in items if i['collection'] == a]
        archival_collections_list.append(item_dict)
    collections_output = args.outfile + "-collections.csv"
    write_file(archival_collections_list, collections_output)
    
    # 
    files_output = args.outfile + "-files.csv"
    write_file(files, files_output)

#============
# call main
#============
if __name__ == "__main__":
    main()
