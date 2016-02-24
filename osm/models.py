from osm import max_bbox, osm_func, osc_func, get_bbox_shape

import re
import redis

import xml.etree.ElementTree as ET


CREATE = "create"
MODIFY = "modify"
DELETE = "delete"
BOUNDS = "bounds"


class Refs:
    NODE = 0
    WAY = 1
    RELATION = 2

    def __init__(self):
        self.nodes = {}
        self.ways = {}
        self.relations = {}

    def put(self, k, v):
        if isinstance(v, Node):
            self.put_node(k, v)
        elif isinstance(v, Way):
            self.put_way(k, v)
        elif isinstance(v, Relation):
            self.put_rel(k, v)

    def put_node(self, k, v):
        if k not in self.nodes:
            self.nodes[k] = v

    def put_way(self, k, v):
        if k not in self.ways:
            self.ways[k] = v

    def put_rel(self, k, v):
        if k not in self.relations:
            self.relations[k] = v

    def get_node(self, k):
        try:
            return self.nodes[k]
        except KeyError:
            return None

    def get_way(self, k):
        try:
            return self.ways[k]
        except KeyError:
            return None

    def get_relation(self, k):
        try:
            return self.relations[k]
        except KeyError:
            return None

    def populate_nodes(self, context):
        for event, elem in context:
            if elem.tag == "node":
                osm_id = elem.attrib["id"]
                lon = elem.attrib["lon"]
                lat = elem.attrib["lat"]
                version = elem.attrib["version"]
                timestamp = elem.attrib["timestamp"]
                self.nodes[osm_id] = Node(
                    osm_id,
                    lon,
                    lat,
                    version,
                    timestamp
                )
            if elem.tag == "way" or elem.tag == "relation":
                break
            elem.clear()


class OSMData:
    def get_bbox(self):
        return get_bbox_shape(self.bounds())


class Node(OSMData):
    TAG = "node"

    def __init__(self, osm_id, lon, lat, version, timestamp):
        self.osm_id = osm_id
        self.lon = lon
        self.lat = lat
        self.version = version
        self.timestamp = timestamp

    def bounds(self):
        return (self.lon, self.lat, self.lon, self.lat)

    def to_xml(self):
        return ET.Element(
            'node',
            id=self.osm_id,
            lon=str(self.lon),
            lat=str(self.lat),
            version=self.version,
            timestamp=self.timestamp
        )

    @staticmethod
    def from_xml(xml):
        osm_id = xml.attrib['id']
        lon = float(xml.attrib['lon'])
        lat = float(xml.attrib['lat'])
        timestamp = xml.attrib['timestamp']
        version = xml.attrib['version']
        return Node(osm_id, lon, lat, version, timestamp)


class Way(OSMData):
    TAG = "way"

    def __init__(self, osm_id, version, timestamp, nodes=None):
        self.osm_id = osm_id
        self.version = version
        self.timestamp = timestamp
        self.nodes = nodes or []

    def bounds(self):
        return reduce(max_bbox, [node.bounds() for node in self.nodes])

    def to_xml(self):
        way_root = ET.Element(
            'way',
            id=self.osm_id,
            version=self.version,
            timestamp=self.timestamp
        )

        for node in self.nodes:
            ET.SubElement(way_root, 'nd', ref=node.osm_id)
        return way_root

    @staticmethod
    def from_xml(xml, refs):
        osm_id = xml.attrib['id']
        timestamp = xml.attrib['timestamp']
        version = xml.attrib['version']
        nodes = []
        for node in xml:
            if node.tag == "nd":
                found_node = refs.get_node(node.attrib['ref'])
                if found_node is not None:
                    nodes.append(found_node)
        if nodes:
            return Way(osm_id, version, timestamp, nodes)


class Relation(OSMData):
    TAG = "relation"

    def __init__(self, osm_id, version, timestamp, members=None):
        self.osm_id = osm_id
        self.version = version
        self.timestamp = timestamp
        self.members = members or []

    def bounds(self):
        return reduce(max_bbox, [member.bounds() for member in self.members])

    def to_xml(self):
        rel_root = ET.Element(
            'relation',
            id=self.osm_id,
            version=self.version,
            timestamp=self.timestamp
        )

        for member in self.members:
            ET.SubElement(rel_root, member.tag, ref=member.osm_id)
        return rel_root

    @staticmethod
    def from_xml(xml, refs):
        osm_id = xml.attrib['id']
        timestamp = xml.attrib['timestamp']
        version = xml.attrib['version']
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
                    found_member = ref_get(member.attrib['ref'])
                    if found_member is not None:
                        members.append(found_member)
        if members:
            return Relation(osm_id, version, timestamp, members)


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
    def from_xml(xml, context):
        elements = []
        refs = Refs()
        refs.populate_nodes(context)

        for element in xml:
            func = osm_func(
                element.tag,
                lambda: Node.from_xml(element),
                lambda: Way.from_xml(element, refs),
                lambda: Relation.from_xml(element, refs)
            )
            if func:
                value = func()
                if value:
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

        for deletion in self.delete:
            deletions.append(delete.to_xml())

        return osc_root

    @staticmethod
    def from_xml(xml, new_context, old_context):
        create = []
        modify = []
        delete = []
        refs = Refs()

        first = True
        for context in [new_context, old_context]:
            if first:
                print "Getting first refs"
            else:
                print "Getting second refs"
            first = False
            refs.populate_nodes(context)

        print "Parsing changes"
        for change_t in xml.getroot():
            for element in change_t:
                if element.tag == BOUNDS:
                    continue
                func = osm_func(
                    element.tag,
                    lambda: Node.from_xml(element),
                    lambda: Way.from_xml(element, refs),
                    lambda: Relation.from_xml(element, refs)
                )
                if func is not None:
                    value = func()
                    if value is not None:
                        refs.put(value.osm_id, value)
                        ctype = osc_func(change_t.tag, create, modify, delete)
                        if ctype is not None:
                            ctype.append(value)
        return OSMChange(create, modify, delete)
