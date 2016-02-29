from setuptools import setup, find_packages
setup(
    name = "rutgers-osm",
    version = "0.1",
    packages = find_packages(),
    package_data = {
        'rutgers-osm': ['wkt/*.wkt']
    }
)
