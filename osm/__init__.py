from osm import models

def osm_func(etype, node, way, relation):
    if etype == "node":
        return node
    elif etype == "way":
        return way
    elif etype == "relation":
        return relation
    else:
        return None


