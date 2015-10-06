from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from osm import osm2pgsql

engine = create_engine('postgresql:///gis')

Session = sessionmaker(bind=engine)
session = Session()
