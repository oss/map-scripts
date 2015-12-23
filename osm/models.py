import xml.etree.ElementTree as ET
from osm import max_bbox, osm_func, osc_func, get_bbox_shape

CREATE = "create"
MODIFY = "modify"
DELETE = "delete"

BOUNDS = "bounds"

class Refs:
    NODE = 0
    WAY = 1
    RELATION = 2

    def __init__(self):
        self.node_refs = {}
        self.way_refs = {}
        self.rel_refs = {}

    def put(self, k, v):
        if v is Node:
            self.put_node(k, v)
        elif v is Way:
            self.put_way(k, v)
        elif v is Relation:
            self.put_rel(k, v)

    def put_node(self, k, v):
        if k not in self.node_refs:
            self.node_refs[k] = v

    def put_way(self, k, v):
        if k not in self.way_refs:
            self.way_refs[k] = v

    def put_rel(self, k, v):
        if k not in self.rel_refs:
            self.rel_refs[k] = v

    def get_node(self, ref):
        return self.get(ref, Refs.NODE)

    def get_way(self, ref):
        return self.get(ref, Refs.WAY)

    def get_relation(self, ref):
        return self.get(ref, Refs.RELATION)

    def get(self, ref, ref_type):
        if ref_type == Refs.NODE:
            return self.node_refs[ref]
        elif ref_type == Refs.WAY:
            return self.way_refs[ref]
        elif ref_type == Refs.RELATION:
            return self.rel_refs[ref]
        else:
            return None


class Node:
    TAG = "node"

    def __init__(self, osm_id, lat, lon):
        self.osm_id = osm_id
        self.lat = lat
        self.lon = lon

    def get_bbox(self):
        return get_bbox_shape(self.bounds())

    def bounds(self):
        return (self.lat, self.lon, self.lat, self.lon)

    def to_xml(self):
        return ET.Element('node', id=self.osm_id, lat=self.lat, lon=self.lon)

    @staticmethod
    def from_xml(xml):
        osm_id = xml.attrib['id']
        lat = xml.attrib['lat']
        lon = xml.attrib['lon']
        return Node(osm_id, lat, lon)


class Way:
    TAG = "way"

    def __init__(self, osm_id, nodes=None):
        self.osm_id = osm_id
        self.nodes = nodes or []

    def get_bbox(self):
        return get_bbox_shape(self.bounds())

    def bounds(self):
        return reduce(max_bbox, [node.bounds() for node in self.nodes])

    def to_xml(self):
        way_root = ET.Element('way', id=self.osm_id)
        for node in self.nodes:
            ET.SubElement(way_root, 'nd', ref=node.osm_id)
        return way_root

    @staticmethod
    def from_xml(xml, refs):
        osm_id = xml.attrib['id']
        nodes = []
        for node in xml:
            if node.tag == "nd":
                nodes.append(refs.get_node(node.attrib['ref']))
        return Way(osm_id, nodes)


class Relation:
    TAG = "relation"

    def __init__(self, osm_id, members=None):
        self.osm_id = osm_id
        self.members = members or []

    def get_bbox(self):
        return get_bbox_shape(self.bounds())

    def bounds(self):
        return reduce(max_bbox, [member.bounds() for node in self.members])

    def to_xml(self):
        rel_root = ET.Element('relation', id=self.osm_id)
        for member in self.members:
            ET.SubElement(rel_root, member.tag, ref=member.osm_id)
        return rel_root

    @staticmethod
    def from_xml(xml, refs):
        osm_id = xml.attrib['id']
        members = []
        for member in xml:
            if member.tag == "member":
                ref_get = osm_func(
                    member.attrib['type'],
                    refs.get_node,
                    refs.get_way,
                    refs.get_relation
                )
                if ref_get:
                    members.append(ref_get(member.attrib['ref']))
        return Relation(osm_id, members)


class OSM:
    def __init__(self, elements=None):
        self.elements = elements or []

    def bounds(self):
        return (self.shape.bounds or
                reduce(max_bbox, [element.bounds() for node in self.elements]))

    def to_xml(self):
        osm_root = ET.Element('osm', version='0.6')
        for element in self.elements:
            osm_root.append(element.to_xml())
        return osm_root

    @staticmethod
    def from_xml(xml):
        elements = []
        refs = Refs()
        for element in xml:
            print "On element: " + element.tag
            func = osm_func(
                element.tag,
                lambda: Node.from_xml(element),
                lambda: Way.from_xml(element, refs),
                lambda: Relation.from_xml(element, refs)
            )
            if func:
                value = func()
                refs.put(value.osm_id, value)
                elements.append(value)
        return OSM(elements)


class OSMChange:
    """Simple wrapper for creating an osmChange.
    Create, modify, and delete are easily accessible
    from the functions provided here. They should mostly be
    appended to.
    """

    def __init__(self, create, modify, delete):
        self.create = create
        self.modify = modify
        self.delete = delete

    def __repr__(self):
        return "OSMChange(create={}, modify={}, delete={})".format(
            str(self.create), str(self.modify), str(self.delete))

    def to_xml(self):
        osc_root = ET.Element('osmChange', version='0.6')
        creations = ET.SubElement(osc_root, "create")
        modifications = ET.SubElement(osc_root, "modify")
        deletions = ET.SubElement(osc_root, "delete")

        for creation in self.create:
            creations.append(creation.to_xml())

        for modification in self.modify:
            modifications.append(modification.to_xml())

        for deletions in self.delete:
            deletions.append(delete.to_xml())

        return osc_root



    @staticmethod
    def from_xml(xml, context):
        create = []
        modify = []
        delete = []
        refs = Refs()

        print "Getting refs"
        for event, elem in context:
            if elem.tag == "node":
                refs.put_node(elem.attrib["id"],
                    Node(
                        elem.attrib["id"],
                        float(elem.attrib["lat"]),
                        float(elem.attrib["lon"])
                    )
                )
            elem.clear()
            while elem.getprevious() is not None:
                del elem.getparent()[0]

        print "Parsing changes"
        for change_t in xml.getroot():
            for element in change_t:
                if element.tag == BOUNDS:
                    # TODO record what the bounds are
                    # reason I don't already is that I don't trust osm
                    continue
                func = osm_func(
                    element.tag,
                    lambda: Node.from_xml(element),
                    lambda: Way.from_xml(element, refs),
                    lambda: Relation.from_xml(element, refs)
                )
                if func is not None:
                    value = func()
                    refs.put(value.osm_id, value)
                    ctype = osc_func(change_t.tag, create, modify, delete)
                    if ctype is not None:
                        ctype.append(value)
        return OSMChange(create, modify, delete)
