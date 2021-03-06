from rutgers_osm import max_bbox, osm_func, osc_func, get_bbox_shape
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
        for elem in context.getroot():
            if elem.tag == "node":
                node = Node.from_xml(elem)
                self.put_node(node.osm_id, node)
            if elem.tag == "way" or elem.tag == "relation":
                break


class OSMData(object):
    def __init__(self, tags=None, **kwargs):
        self.osm_id = kwargs["id"]
        del kwargs["id"]

        self.tags = tags or {}
        self.kwargs = kwargs

    def tags_to_xml(self, root):
        for tag in self.tags:
            ET.SubElement(root, 'tag', k=tag, v=self.tags[tag])

    def get_bbox(self):
        return get_bbox_shape(self.bounds())

    @staticmethod
    def tags_from_xml(xml):
        tags = {}
        for tag in xml:
            if tag.tag == "tag":
                tags[tag.attrib['k']] = tag.attrib['v']
        return tags


class Node(OSMData):
    TAG = "node"

    def __init__(self, tags=None, **kwargs):
        super(Node, self).__init__(tags, **kwargs)

        self.lon = float(kwargs["lon"])
        self.lat = float(kwargs["lat"])

    def bounds(self):
        return (self.lon, self.lat, self.lon, self.lat)

    def to_xml(self):
        node_root = ET.Element('node', id=self.osm_id, **self.kwargs)
        self.tags_to_xml(node_root)
        return node_root

    @staticmethod
    def from_xml(xml):
        tags = OSMData.tags_from_xml(xml)
        return Node(tags, **xml.attrib)


class Way(OSMData):
    TAG = "way"

    def __init__(self, nodes=None, tags=None, **kwargs):
        super(Way, self).__init__(tags, **kwargs)
        self.nodes = nodes or []

    def bounds(self):
        return reduce(max_bbox, [node.bounds() for node in self.nodes])

    def to_xml(self):
        way_root = ET.Element('way', id=self.osm_id, **self.kwargs)

        for node in self.nodes:
            ET.SubElement(way_root, 'nd', ref=node.osm_id)

        self.tags_to_xml(way_root)

        return way_root

    @staticmethod
    def from_xml(xml, refs):
        nodes = []
        tags = OSMData.tags_from_xml(xml)
        for e in xml:
            if e.tag == "nd":
                found_node = refs.get_node(e.attrib['ref'])
                if found_node is not None:
                    nodes.append(found_node)
        if nodes:
            return Way(nodes, tags, **xml.attrib)


class Relation(OSMData):
    TAG = "relation"

    def __init__(self, members=None, tags=None, **kwargs):
        super(Relation, self).__init__(tags, **kwargs)
        self.members = members or []

    def bounds(self):
        return reduce(max_bbox, [member.bounds() for member, role in self.members])

    def to_xml(self):
        rel_root = ET.Element('relation', id=self.osm_id, **self.kwargs)

        for member, role in self.members:
            ET.SubElement(rel_root, "member", type=member.TAG, ref=member.osm_id, role=role)

        self.tags_to_xml(rel_root)

        return rel_root

    @staticmethod
    def from_xml(xml, refs):
        tags = OSMData.tags_from_xml(xml)
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
                        members.append((found_member, member.attrib['role']))
        if members:
            return Relation(members, tags, **xml.attrib)


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
            deletions.append(deletion.to_xml())

        return osc_root

    @staticmethod
    def from_xml(xml, *contexts):
        create = []
        modify = []
        delete = []
        refs = Refs()

        for i, context in enumerate(contexts):
            print "Parsing refs {0} of {1}".format(i + 1, len(contexts))
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
