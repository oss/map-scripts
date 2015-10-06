from sqlalchemy import create_engine, Column, Integer, String, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import sessionmaker
from geoalchemy2 import Geometry
from geoalchemy2.shape import to_shape
from pyproj import Proj

from osm.models import Node, Way, Relation

Base = declarative_base()

class DBPoint(Base):
    __tablename__ = 'planet_osm_point'

    osm_id = Column(BigInteger, primary_key=True)
    way = Column(Geometry('POINT'))


class DBNode(Base):
    __tablename__ = 'planet_osm_nodes'

    id = Column(BigInteger, primary_key=True)
    lat = Column(Integer)
    lon = Column(Integer)


class DBLine(Base):
    __tablename__ = 'planet_osm_line'

    osm_id = Column(BigInteger, primary_key=True)
    way = Column(Geometry('LINESTRING'))


class DBWay(Base):
    __tablename__ = 'planet_osm_ways'

    id = Column(BigInteger, primary_key=True)
    nodes = Column(postgresql.ARRAY(BigInteger))


class DBPolygon(Base):
    __tablename__ = 'planet_osm_polygon'

    osm_id = Column(BigInteger, primary_key=True)
    way = Column(Geometry('GEOMETRY'))


class Osm2Pgsql():
    def __init__(self, dbname='gis'):
        self.engine = create_engine('postgresql:///{}'.format(dbname))

        Session = sessionmaker(bind=engine)
        self.session = Session()

    def get_node(self, osm_id):
        node = self.session.query(DBPoint).filter_by(osm_id=osm_id).first()
        if node is None:
            node = self.session.query(DBNode).filter_by(id=osm_id).first()
            if node is None:
                return None
            return Node(osm_id, node.lat, node.lon)
        point = to_shape(node.way)
        lat, lon = Proj(init='epsg:3857')(point.x, point.y, inverse=True)
        return Node(osm_id, lat, lon)

    def get_way(self, osm_id):
        way = self.session.query(DBLine).filter_by(osm_id=osm_id).first()
        if way is None:
            way = self.session.query(DBWay).filter_by(id=osm_id).first()
            if way is None:
                return None
            nodes = []
            for node_ref in way.nodes:
                node = self.get_node(node_ref)
                if node is not None:
                    nodes.append(node)
            return Way(osm_id, nodes)
        proj_coords = list(to_shape(way.way).coords)
        coords = [Proj(init='epsg:3857')(x, y, inverse=True) for x, y in proj_coords]
        return Way(osm_id, shape=LineString(coords))

    def get_relation(self, osm_id):
        rel = self.session.query(DBPolygon).filter_by(osm_id=osm_id).first()
        if rel is None:
            return None
