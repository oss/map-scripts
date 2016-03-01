from setuptools import setup, find_packages
setup(
    name = "rutgers-osm",
    version = "0.1",
    packages = find_packages(),
    install_requires = ['shapely'],
    entry_points = {
        'console_scripts': [
            'apply-changes = rutgers_osm.apply_changes:apply_changes',
            'generate-changes = rutgers_osm.generate_changes:generate_changes',
            'generate-tiles = rutgers_osm.generate_tiles:generate_tiles',
            'generate-josm = rutgers_osm.generate_josm:generate_josm_main',
            'get-new-jersey = rutgers_osm.get_new_jersey:get_new_jersey_main'
        ]
    }
)
