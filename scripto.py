#!/usr/bin/env python3

import sys
import json

with open(sys.argv[1], 'r') as f:
    data = json.load(f)
    resp = data['response']['docs']

result = {}

for item in resp:
    pid = item['pid']
    title = item['title']
    if item['hasPart']:
        pages = [item['hasPart'].split(',')]
    print(pid,title,pages)
    
    # if 'dmArchivalCollectionTitle' in item:
#         print(item['dmArchivalCollectionTitle'])
#     else:
#         print("pid")
