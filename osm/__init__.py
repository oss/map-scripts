from shapely.geometry import box, Point, LineString

def osm_func(etype, node, way, relation):
    if etype == "node":
        return node
    elif etype == "way":
        return way
    elif etype == "relation":
        return relation
    else:
        return None


def osc_func(ctype, create, modify, delete):
    if ctype == "create":
        return create
    elif ctype == "modify":
        return modify
    elif ctype == "delete":
        return delete
    else:
        return None


def max_bbox(bbox1, bbox2):
    return (
        min(bbox1[0], bbox2[0]),
        min(bbox1[1], bbox2[1]),
        max(bbox1[2], bbox2[2]),
        max(bbox1[3], bbox2[3])
    )

def get_bbox_shape(bbox):
    if bbox[0] == bbox[2] and bbox[1] == bbox[3]:
        return Point(bbox[0], bbox[1])
    # check if just width xor height is missing
    elif bbox[0] == bbox[2]:
        return LineString([(bbox[1], bbox[3])])
    elif bbox[1] == bbox[3]:
        return LineString([(bbox[0], bbox[2])])
    else:
        return box(*bbox)
