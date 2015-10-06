def load_xml_from_url(url):
    """Turn a url into a parsed ElementTree
    Assumes that the url leads to xml
    """
    f = urllib2.urlopen(url)
    root = ET.fromstring(f.read())
    f.close()
    return root


def get_by_name(name, format='xml', bbox=None):
    """Get a shape based on a string. Use nominatim to get
    the most likely candidate
    """
    name_search = None
    if bbox is not None:
        str_bbox = "{0},{1},{2},{3}".format(*bbox)
        name_search = load_xml_from_url(nominatim_url(name,
                                                  format=format,
                                                  viewboxlbrt=str_bbox,
                                                  polygon_text="1"))
    else:
        name_search = load_xml_from_url(nominatim_url(name, format=format,
                                                  polygon_text="1"))
    return name_search


def name_to_polygon(name, bbox=None):
    name_root = get_by_name(urllib.quote(name), bbox=bbox)
    polygon = loads(name_root[0].attrib['geotext'])
    return polygon


def nominatim_url(query, **kwargs):
    """Build a url for nominatim to get osm info
    from a string
    """
    # base url
    nominatimurl = 'http://nominatim.openstreetmap.org/search/'
    # add on the query
    if query is not None:
        nominatimurl += query
    # return if we're done
    if not kwargs:
        return nominatimurl
    nominatimurl += '?'
    for kwarg in kwargs:
        # only add on the & if we haven't just added on the ?
        if nominatimurl[len(nominatimurl)-1] != '?':
            nominatimurl += '&'
        # put kwarg with the format key=value
        nominatimurl += kwarg + '=' + kwargs[kwarg]
    return nominatimurl
