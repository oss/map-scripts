def osm_func(etype, node, way, relation):
    if etype == "node":
        return node
    elif etype == "way":
        return way
    elif etype == "relation":
        return relation
    else:
        return None


def max_bbox(bbox1, bbox2):
    return (
        min(bbox1[0], bbox2[0]),
        min(bbox1[1], bbox2[1]),
        max(bbox1[2], bbox2[2]),
        max(bbox1[3], bbox2[3])
    )
