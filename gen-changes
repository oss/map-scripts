#!/usr/bin/env python

import os
import os.path
import shutil
import smtplib
import subprocess
import urllib2
import xml.etree.ElementTree as ET
import xml.dom.minidom as MD
from email import Encoders
from email.MIMEBase import MIMEBase
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.Utils import formatdate

import argparse

from rutgers_osm.models import OSMChange, max_bbox
import rutgers_osm.osmosis as osmosis

from shapely.wkt import loads

# URL for latest NJ pbf
NJ_LATEST = ("http://download.geofabrik.de/"
             "north-america/us/new-jersey-latest.osm.pbf")

# Disk locations for latest and previous NJ pbf
NJ_LATEST_PBF = '/army/new-jersey-latest.osm.pbf'
NJ_LATEST_SMALL = '/army/new-jersey-latest-small.osm'
NJ_OLD_PBF = '/army/new-jersey-old.osm.pbf'
NJ_OLD_SMALL = '/army/new-jersey-old-small.osm'

# Diff and changes disk locations
DIFF = '/army/diff.osc'
CHANGES = '/army/changes'
PENDING = '/army/pending'

TMPFILE = '/tmp/map_scripts_tmp.osm'


def pretty_ET(root):
    """Pretty print xml from ElementTree"""
    return MD.parseString(ET.tostring(root)).toprettyxml()


def send_mail(changes, address):
    """Send email requesting maps approval."""
    msg = MIMEMultipart()
    msg['From'] = 'phantoon'
    msg['To'] = address
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = "Changes for Rutgers maps need approval"
    msg.attach(MIMEText(
        "The attached files need approval, run "
        "'/usr/bin/commit-changes' on phantoon to allow or deny changes"))
    for change in changes:
        part = MIMEBase('text', 'xml')
        part.set_payload(open(change, "r").read())
        Encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="{0}"'.
                        format(os.path.basename(change)))
        msg.attach(part)
    smtp = smtplib.SMTP('localhost')
    smtp.sendmail('phantoon', address, msg.as_string())
    smtp.close()


def get_new_jersey(outfile, nj_latest):
    """Download latest version of New Jersey from geofabrik"""
    with open(outfile, 'w') as f:
        f.write(urllib2.urlopen(nj_latest).read())


def lowest_avail_id(directory):
    current_ids = set(
        [int(os.path.splitext(f)[0]) for f in os.listdir(directory)])

    lowest_id = 1
    while lowest_id in current_ids:
        lowest_id += 1

    return lowest_id


def lowest_avail_filename(directory):
    return os.path.join(directory, str(lowest_avail_id(directory)) + '.osc')


def get_shape_from_file(filename):
    with open(filename) as f:
        shape = loads(f.read().strip('\n'))
        return shape


def get_rutgers():
    campuses = ["busch", "livingston", "college_avenue", "cook"]
    return filter(
        lambda x: x is not None,
        [get_shape_from_file(campus + ".wkt") for campus in campuses]
    )


def intersects_any(bbox, rutgers):
    for campus in rutgers:
        if bbox.intersects(campus):
            return True
    return False


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description='Create change files based on a bounding box')
    parser.add_argument('-u', '--nj-url',
                        default=NJ_LATEST,
                        help='Url to get pbf from')
    parser.add_argument('-L', '--nj-latest',
                        default=NJ_LATEST_PBF,
                        help='Location to save new pbf')
    parser.add_argument('-l', '--nj-latest-small',
                        default=NJ_LATEST_SMALL,
                        help='Location to store new NJ crop')
    parser.add_argument('-O', '--nj-old',
                        default=NJ_OLD_PBF,
                        help='Location of the old pbf')
    parser.add_argument('-o', '--nj-old-small',
                        default=NJ_OLD_SMALL,
                        help='Location to store old NJ crop')
    parser.add_argument('-d', '--diff',
                        default=DIFF,
                        help='Diff location')
    parser.add_argument('-c', '--changes',
                        default=CHANGES,
                        help='Changes directory')
    parser.add_argument('-p', '--pending',
                        default=PENDING,
                        help='Pending directory')
    parser.add_argument('-s', '--short-circuit',
                        action='store_true')
    parser.add_argument('-m', '--no-send-mail',
                        action='store_true',
                        help='Add to stop mail sending')
    parser.add_argument('-t', '--tmp-file',
                        default=TMPFILE,
                        help='Location of temp file')
    args = parser.parse_args()

    rutgers = get_rutgers()
    rutgers_bbox = reduce(max_bbox, [campus.bounds for campus in rutgers])

    if not args.short_circuit:
        print "Moving old New Jersey file"
        shutil.move(args.nj_latest, args.nj_old)

        print "Getting new New Jersey file"
        get_new_jersey(args.nj_latest, args.nj_url)

        latest_crop_cmd = osmosis.crop(args.nj_latest, rutgers_bbox, args.nj_latest_small)
        old_crop_cmd = osmosis.crop(args.nj_old, rutgers_bbox, args.nj_old_small)
        crop_diff_cmd = osmosis.diff(args.nj_latest_small, args.nj_old_small, args.diff, format="xml")

        print "Running the following commands"
        print latest_crop_cmd
        print old_crop_cmd
        print crop_diff_cmd
        print ""

        print "Calling osmosis"
        subprocess.check_call(latest_crop_cmd)
        subprocess.check_call(old_crop_cmd)
        subprocess.check_call(crop_diff_cmd)

    print "Parsing diff"
    changes = OSMChange.from_xml(
        ET.parse(args.diff),
        ET.parse(args.nj_latest_small),
        ET.parse(args.nj_old_small)
    )

    ask_create = []
    ask_modify = []
    ask_delete = []

    split_changes = [
        (ask_create, changes.create),
        (ask_modify, changes.modify),
        (ask_delete, changes.delete)
    ]

    print "Checking intersections"
    for ask_change, change in split_changes:
        for element in change:
            if intersects_any(element.get_bbox(), rutgers):
                ask_change.append(element)

    ask_changes = OSMChange(ask_create, ask_modify, ask_delete)

    print "Writing intersections to disk"
    pending_filename = lowest_avail_filename(args.pending)
    with open(pending_filename, 'w') as f:
        f.write(pretty_ET(ask_changes.to_xml()).encode('utf-8'))

    print "Getting non-intersecting changes"
    apply_cmd = osmosis.apply_diff(args.nj_old, pending_filename, args.tmp_file)
    subprocess.check_call(apply_cmd)

    print "Writing non-intersecting changes to disk"
    apply_filename = lowest_avail_filename(args.changes)
    diff_cmd = osmosis.diff(args.tmp_file, args.nj_latest, apply_filename)
    subprocess.check_call(diff_cmd)

    os.remove(args.tmp_file)

    if not args.no_send_mail:
        print "Sending mail"
        send_mail([apply_filename, pending_filename],
                  'mwr54@nbcs.rutgers.edu')
