import xml.etree.ElementTree as ET
from osm import max_bbox, osm_func, osc_func, get_bbox_shape
import redis
import re

CREATE = "create"
MODIFY = "modify"
DELETE = "delete"

BOUNDS = "bounds"

NODE_KEY = re.compile("(.+):(.+)")
WAY_KEY = re.compile("node:(\d+)")
REL_KEY = re.compile("(\w+):(\d+)")

class Refs:
    NODE = 0
    WAY = 1
    RELATION = 2

    def __init__(self):
        self.r = redis.Redis(host="localhost", port=6379)

    def put(self, k, v):
        if isinstance(v, Node):
            self.put_node(k, v)
        elif isinstance(v, Way):
            self.put_way(k, v)
        elif isinstance(v, Relation):
            self.put_rel(k, v)

    def set(self, k, v):
        if self.get(k) is None:
            self.r.set(k, v)

    def get(self, k):
        return self.r.get(k)

    def put_node(self, k, v):
        if self.r.get("node:{0}".format(k)) is not None:
            return

        self.r.set(
            "node:{0}".format(k),
            "{0}:{1}".format(v.lat, v.lon)
        )

    def put_way(self, k, v):
        if self.r.get("way:{0}".format(k)) is not None:
            return

        for node in v.nodes:
            self.r.rpush(
                "way:{0}".format(k),
                "node:{0}".format(node.osm_id)
            )

    def put_rel(self, k, v):
        if self.r.get("relation:{0}".format(k)) is not None:
            return

        for member in v.members:
            self.r.rpush(
                "relation:{0}".format(k),
                "{0}:{1}".format(member.TAG, member.osm_id)
            )

    def get_node(self, k):
        v = self.r.get("node:{0}".format(k))
        if v is None:
            return None

        lat, lon = NODE_KEY.search(v).group(0, 1)
        return Node(k, float(lat), float(lon))

    def get_way(self, k):
        v = self.r.get("way:{0}".format(k))
        if v is None:
            return None

        nodes = []
        for node in v:
            node_k = WAY_KEY.search(node).group(0)
            nodes.append(self.get_node(node_k))
        return Way(k, nodes)

    def get_relation(self, k):
        v = self.r.get("relation:{0}".format(k))
        if v is None:
            return None

        members = []
        for member in v:
            member_type, member_id = REL_KEY.search(member).group(0, 1)
            if member_type == "node":
                append_value = self.get_node(member_id)
            elif member_type == "way":
                append_value = self.get_way(member_id)
            else:
                append_value = self.get_relation(member_id)
            members.append(append_value)
        return Relation(k, members)

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
        lat = float(xml.attrib['lat'])
        lon = float(xml.attrib['lon'])
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
                found_node = refs.get_node(node.attrib['ref'])
                if found_node is not None:
                    nodes.append(found_node)
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
                    found_member = ref_get(member.attrib['ref'])
                    if found_member is not None:
                        members.append(found_member)
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
            for event, elem in context:
                if elem.tag == "node":
                    refs.set(
                        "node:{0}".format(elem.attrib["id"]),
                        "{0}:{1}".format(elem.attrib["lat"], elem.attrib["lon"])
                    )
                if elem.tag == "way" or elem.tag == "relation":
                    break
                elem.clear()

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
