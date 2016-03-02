from setuptools import setup, find_packages
setup(
    name = "rutgers-osm",
    version = "0.3.2",
    packages = find_packages(),
    install_requires = ['shapely'],
    entry_points = {
        'console_scripts': [
            'apply-changes = rutgers_osm.apply_changes:apply_changes_main',
            'generate-changes = rutgers_osm.generate_changes:generate_changes_main',
            'generate-tiles = rutgers_osm.generate_tiles:generate_tiles_main',
            'generate-josm = rutgers_osm.generate_josm:generate_josm_main',
            'get-new-jersey = rutgers_osm.get_new_jersey:get_new_jersey_main'
        ]
    }
)
