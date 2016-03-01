import argparse
import os
import shutil

PREFIX = '/army'
PENDING = os.path.join(PREFIX, 'pending')
CHANGES = os.path.join(PREFIX, 'changes')


def commit_changes():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--all', action='store_true')
    parser.add_argument('ids', metavar='IDs', type=int, nargs='*')
    args = parser.parse_args()

    paths = os.listdir(PENDING) if args.all else '{0}.osc'.format(args.ids)

    for path in paths:
        pending = os.path.join(path, PENDING)
        try:
            shutil.move(pending, CHANGES)
        except IOError as e:
            print "Error: {0}".format(pending)
            print e

    print "Done!"
