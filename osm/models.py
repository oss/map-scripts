import xml.etree.ElementTree as ET
from osm import max_bbox

class Refs:
    NODE = 0
    WAY = 1
    RELATION = 2

    def __init_(self, refs):
        self.refs = refs

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
        if nodes is None:
            self.nodes = []
        else:
            self.nodes = nodes

    def bounds(self):
        if self.shape is not None:
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
        if members is None:
            self.members = []
        else:
            self.members = members

    def bounds(self):
        if self.shape is not None:
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
                func = osm_func(
                    member.attrib['type'],
                    refs.get_node,
                    refs.get_way,
                    refs.get_relation
                )
                if func is not None:
                    members.append(func(member.attrib['ref']))
        return Relation(osm_id, members)


class OSM:
    def __init__(self, elements=None):
        if elements is None:
            self.elements = []
        else:
            self.elements = elements

    def bounds(self):
        if self.shape is not None:
            return self.shape.bounds
        return reduce(max_bbox, [element.bounds() for node in self.elements])

    def to_xml(self):
        osm_root = ET.Element('osm', version='0.6')
        for element in self.elements:
            osm_root.append(element.to_xml())
        return osm_root

    @staticmethod
    def from_xml(xml):
        elements = []
        refs = {}
        for element in xml:
            func = osm_func(
                element.tag,
                lambda: Node.from_xml(element),
                lambda: Way.from_xml(element, refs),
                lambda: Relation.from_xml(element, refs)
            )
            if func is not None:
                value = func()
                refs.put(value)
                elements.append(value)
        return OSM(elements)


class OSMChange:
    """Simple wrapper for creating an osmChange.
    Create, modify, and delete are easily accessible
    from the functions provided here. They should mostly be
    appended to.
    """
    def __init__(self, xml=None):
        self.osc = ET.Element('osmChange')
        self.osc.set('version', '0.6')
        self.create = ET.SubElement(self.osc, 'create')
        self.modify = ET.SubElement(self.osc, 'modify')
        self.delete = ET.SubElement(self.osc, 'delete')

    def __repr__(self):
        return ET.tostring(self.osc)

    def dump(self):
        ET.dump(self.osc)
