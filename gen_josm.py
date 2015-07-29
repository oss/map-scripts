import urllib2
import xml.etree.ElementTree as ET
import xml.dom.minidom
import Polygon, Polygon.IO
import argparse
from scipy import spatial


class Way():
    """Object representation of ways. Has all nodes and an
    average point
    """
    def __init__(self, way, nodes):
        self.nodes = []
        self.tags = {}
        self.avg_point = [0, 0]
        self.attrib = way.attrib
        coords = []
        for nd in way.findall('nd'):
            node = nodes[nd.attrib['ref']]
            self.nodes.append(node)
            x = float(node.attrib['lon'])
            y = float(node.attrib['lat'])
            coords.append([x, y])
            self.avg_point[0] += x
            self.avg_point[1] += y
        self.polygon = Polygon.Polygon(coords)
        self.avg_point[0] /= len(self.nodes)
        self.avg_point[1] /= len(self.nodes)
        for tag in way.findall('tag'):
            self.tags[tag.attrib['k']] = tag.attrib['v']

    def get_bounds(self):
        """Find a bouding box around a way"""
        box = [180, 90, -180, -90]
        for node in self.nodes:
            lon = float(node.attrib['lon'])
            lat = float(node.attrib['lat'])
            if lon <= box[0]:
                box[0] = lon
            if lat <= box[1]:
                box[1] = lat
            if lon >= box[2]:
                box[2] = lon
            if lat >= box[3]:
                box[3] = lat
        return box

def make_ways(root):
    """Build way objects from the root of an osm file"""
    nodes = {}
    ways = []
    for node in root.findall('node'):
        nodes[node.attrib['id']] = node

    for way in root.findall('way'):
        building = False
        for tag in way.findall('tag'):
            if tag.attrib['k'] == "building" and tag.attrib['v'] == "yes":
                building = True
        if building:
            ways.append(Way(way, nodes))

    return ways

def largest_box(boxes):
    """Find the largest box that surrounds any of the boxes in the list.
    Otherwise known as a bouding box for boxes
    """
    largest = [str(min([box[x] for box in boxes])) for x in [0, 1]]
    largest.extend([str(max([box[x] for box in boxes])) for x in [2, 3]])
    return largest

def anything_inside(box, ways):
    """Check if any of the ways are inside the box"""
    pass

def get_subdivisions(box, url, ways):
    """Divide the given box into a list of boxes. Each box will have few enough
    elements to be queried with the given url (osm max queries is 2000).

    returns: a list of boxes
    """
    x0 = box[0]
    y0 = box[1]
    x1 = box[2]
    y1 = box[3]
    boxes = []
    try:
        urllib2.urlopen(url.format(*box))
        boxes.append(box)
    except urllib2.HTTPError:
        center = [(x1 - x0) / 2.0, (y1 - y0) / 2.0]
        subdivisions = [
                        [x0, center[1], center[0], y1],
                        [center[0], center[1], x1, y1],
                        [x0, y0, center[0], center[1]],
                        [center[0], y0, x1, center[1]]]
        for subdivision in subdivisions:
            if anything_inside(subdivision, ways):
                boxes.append(get_subdivisions(subdivision, url, ways))
    return boxes


def get_api_url(debug=False):
    """Get the osm api url for bounding boxes. To use the debug
    api, set debug to true. Returns a string that should be formated
    with each coordinate
    """
    base_apiurl = 'http://api.openstreetmap.org' if debug == False else 'http://api06.dev.openstreetmap.org'
    return base_apiurl + '/api/0.6/map?bbox={0},{1},{2},{3}'

def jaccard_similarity(pair, similarity):
    """Find the similarities between a group of ways.
    Returns a pair of ways; the first one replaces the right. The second value is none
    if the pairs do not match
    """
    intersect = pair[0].polygon & pair[1].polygon
    union = pair[0].polygon | pair[1].polygon
    jaccard = intersect.area() / union.area()
    if jaccard >= float(similarity) / 100:
        return pair
    else:
        return [pair[0], None]

def make_relations(root, pair):
    ret = []
    if pair[1] is not None:
        relations = root.findall('relation')
        for relation in relations:
            members = relation.findall('member')
            for member in members:
                if member.attrib['type'] == "way" and member.attrib['ref'] == pair[1].attrib['id']:
                    relation.attrib['action'] = 'modify'
                    ret.append(relation)
                    break
    return ret

def generate_josm(pairs):
    """Make josm from pairs of ways to be replaced
    Returns the root node in an ElementTree
    """
    # Make root of output xml
    josm_root = ET.Element('osm', {'version': "0.6", 'generator': "gen_josm"})
    ET.SubElement(josm_root, 'bounds', {'minlat': largest_bound[0], 'minlon': largest_bound[1], 'maxlat': largest_bound[2], 'maxlon': largest_bound[3], 'origin': 'gen_josm'})

    # Generate nodes then ways in output xml
    # place_id is a new id (JOSM specifies a negative id as a new entry
    # TODO regenerate relationships
    place_id = -1
    for pair in pairs:
        nodes = []
        for node in pair[0].nodes:
            e_node = ET.SubElement(josm_root, 'node', node.attrib)
            e_node.attrib['id'] = str(place_id)
            nodes.append(e_node)
            place_id -= 1
            for tag in node.findall('tag'):
                ET.SubElement(e_node, 'tag', tag.attrib)
                e_node.attrib['id'] = str(place_id)
                place_id -= 1
        way = ET.SubElement(josm_root, 'way', pair[0].attrib)
        way.attrib['id'] = str(place_id)
        for relation in pair[2]:
            for member in relation.findall('member'):
                if member.attrib['type'] == "way" and member.attrib['ref'] == pair[1].attrib['id']:
                    member.attrib['ref'] = way.attrib['id']
        place_id -= 1
        for nd in nodes:
            ET.SubElement(way, 'nd', {'ref': nd.attrib['id']})
        for key in pair[0].tags:
            ET.SubElement(way, 'tag', {'k': key, 'v': pair[0].tags[key]})
        if pair[1] is not None:
            for node in pair[1].nodes:
                d_node = ET.SubElement(josm_root, 'node', node.attrib)
                d_node.attrib['action'] = 'delete'
            d_way = ET.SubElement(josm_root, 'way', pair[1].attrib)
            d_way.attrib['action'] = 'delete'
    uni_relation = []
    for pair in pairs:
        for relation in pair[2]:
            if int(relation.attrib['id']) not in uni_relation:
                uni_relation.append(int(relation.attrib['id']))
                e_rela = ET.SubElement(josm_root, 'relation', relation.attrib)
                for member in relation.findall('member'):
                    ET.SubElement(e_rela, 'member', member.attrib)
                for tag in relation.findall('tag'):
                    ET.SubElement(e_rela, 'tag', tag.attrib)

    return josm_root

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input_osm", help="The osm file you want to use in OSM")
    parser.add_argument("similarity", help="The similarity level between builings between 0 and 100", type=int)
    args = parser.parse_args()

    # Get API url
    boundb_apiurl = get_api_url()

    # Bounding boxes for campuses
    # Parse input data
    our_root = ET.parse(args.input_osm)
    our_ways = make_ways(our_root)

    # Find the bounding box around the given data
    # and split it up into valid locations
    largest_bound = largest_box([way.get_bounds() for way in our_ways])
    locations = get_subdivisions(largest_bound, boundb_apiurl, our_ways)

    # Make an API call for each location and parse the xml returned
    responses = [urllib2.urlopen(boundb_apiurl.format(*location)) for location in locations]
    roots = [ET.fromstring(response.read()) for response in responses]

    osm_ways = []

    # Get all the ways from the xml
    for root in roots:
        osm_ways.extend(make_ways(root))

    # Make a spatial tree from way average points
    osm_tree = spatial.KDTree([way.avg_point for way in osm_ways])

    # Find nearest points and make pairs of guesses based on this
    pairs = []
    for way in our_ways:
        index = osm_tree.query([way.avg_point])[1][0]
        pairs.append([way, osm_ways[index]])

    # Find pairs that are >= the entered amount similar
    # TODO check for other places nodes are used for deletions
    replace_pairs = [jaccard_similarity(pair, args.similarity) for pair in pairs]
    for root in roots:
        for pair in replace_pairs:
            pair.append(make_relations(root, pair))

    josm_root = generate_josm(replace_pairs)

    # Make the xml pretty and print it out
    josm_xml = xml.dom.minidom.parseString(ET.tostring(josm_root))
    print josm_xml.toprettyxml(),
