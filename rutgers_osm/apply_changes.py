import os.path
import shutil
import subprocess
import sys

LOCKDIR = "/var/lock/maps"
LOCK = os.path.join(LOCKDIR, "apply-changes")

CHANGES ="/army/changes"

DTILES = "/army/dirty-tiles"
DTILES_SINGLE = DTILES + "-{0}"

def apply_changes():
    if os.path.isfile(LOCK):
        print "Someone's already applying changes! Check {0}".format(LOCK)
        sys.exit(1)

    if os.path.isfile(DTILES):
        os.remove(DTILES)

    for change in [os.path.join(CHANGES, change_path) for change_path in os.listdir(CHANGES)]:
        changename = os.path.splitext(os.path.basename(change))[0]
        d_t_location = DTILES_SINGLE.format(changename)
        osm2pgsql_cmd = [
            "osm2pgsql",
            "--append",
            "--slim",
            "-d",
            "gis",
            "-C",
            "1600",
            "--number-processes",
            "3",
            "-e0-18",
            "-o",
            d_t_location
        ]

        try:
            subprocess.check_call(osm2pgsql_cmd)
        except:
            continue

        if not os.path.isfile(DTILES):
            shutil.move(d_t_location, DTILES)
        else:
            with open(DTILES, 'a') as dt:
                with open(d_t_location) as dtl:
                    dt.write(dtl.read())
                os.remove(dtl)
        os.remove(change)
    os.remove(LOCK)
