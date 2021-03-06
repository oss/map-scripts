#!/usr/bin/python
from lxml.cssselect import CSSSelector
import lxml.html
import sys
import urllib2
from datetime import datetime

NJ_LATEST = ("http://download.geofabrik.de/"
                     "north-america/us/new-jersey-latest.osm.pbf")

def get_new_jersey(outfile):
    with open(outfile, 'w') as f:
        f.write(urllib2.urlopen(NJ_LATEST).read())

def get_new_jersey_main():
    if len(sys.argv) != 2:
        print "Usage: get-new-jersey <outfile>"
        sys.exit(1)
    get_new_jersey(sys.argv[1])
