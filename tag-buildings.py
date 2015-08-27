import argparse
import xml.etree.ElementTree as ET
import xml.dom.minidom

def create_tags(way):
    for tag in way.findall('tag'):
        if tag.attrib['k'] == "BldgName":
            ET.SubElement(way, 'tag', {'k': "name", 'v': tag.attrib['v']})
            ET.SubElement(way, 'tag', {'k': "building", 'v': "yes"})
        elif tag.attrib['k'] == "BldgAddres":
            ET.SubElement(way, 'tag', {'k': "addr:street", 'v': tag.attrib['v'].title()})
        elif tag.attrib['k'] == "City":
            ET.SubElement(way, 'tag', {'k': "addr:city", 'v': tag.attrib['v'].title()})
        elif tag.attrib['k'] == "Zip":
            ET.SubElement(way, 'tag', {'k': "addr:postcode", 'v': tag.attrib['v']})

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input_osm", help="The osm file you want to use")
    args = parser.parse_args()

    root = ET.parse(args.input_osm).getroot()

    [create_tags(way) for way in root.findall('way')]
    [create_tags(relation) for relation in root.findall('relation')]

    #xml_out = xml.dom.minidom.parseString(ET.tostring(root))
    #print xml_out.toprettyxml(),
    print ET.tostring(root),
