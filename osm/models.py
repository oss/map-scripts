import xml.etree.ElementTree as ET
from osm import max_bbox, osm_func, osc_func

CREATE = "create"
MODIFY = "modify"
DELETE = "delete"

BOUNDS = "bounds"

class Refs:
    NODE = 0
    WAY = 1
    RELATION = 2

    def __init_(self, refs=None):
        self.refs = refs or {}

    def put(self, k, v):
        self.refs[k] = v

    def get_node(self, ref):
        return self.get(ref, Refs.NODE)

    def get_way(self, ref):
        return self.get(ref, Refs.WAY)

    def get_relation(self, ref):
        return self.get(ref, Refs.RELATION)

    def get(self, ref, ref_type):
        try:
            return self.refs[ref]
        except KeyError:
            # query from the database
            # TODO
            if ref_type == Refs.NODE:
                return None
            elif ref_type == Refs.WAY:
                return None
            elif ref_type == Refs.RELATION:
                return None
            else:
                return None


class Node:
    def __init__(self, osm_id, lat, lon):
        self.osm_id = osm_id
        self.lat = lat
        self.lon = lon
        self.tag = 'node'

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
    def __init__(self, osm_id, nodes=None, shape=None):
        self.osm_id = osm_id
        self.tag = 'way'
        self.shape = shape
        self.nodes = nodes or []

    def bounds(self):
        if self.shape:
            return self.shape.bounds
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
    def __init__(self, osm_id, members=None, shape=None):
        self.osm_id = osm_id
        self.tag = 'relation'
        self.shape = shape
        self.members = members or []

    def bounds(self):
        if self.shape:
            return self.shape.bounds
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

    def __init__(self, create=None, modify=None, delete=None):
        self.create = create or []
        self.modify = modify or []
        self.delete = delete or []

    def __repr__(self):
        return ET.tostring(self.osc)

    def dump(self):
        ET.dump(self.osc)

    @staticmethod
    def from_xml(xml):
        create = []
        modify = []
        delete = []
        refs = {}
        for change_t in xml.getroot():
            for element in change_t:
                if element.tag == BOUNDS:
                    # TODO record what the bounds are
                    continue
                func = osm_func(
                    element.tag,
                    lambda: Node.from_xml(element),
                    lambda: Way.from_xml(element, refs),
                    lambda: Relation.from_xml(element, refs)
                )
                if func:
                    value = func()
                    refs.put(value.osm_id, value)
                    ctype = osc_func(change_t.tag, create, modify, delete)
                    if ctype:
                        ctype.append(value)
        return OSMChange(create, modify, delete)
