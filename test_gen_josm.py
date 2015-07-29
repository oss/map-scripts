import unittest
import gen_josm
import xml.etree.ElementTree as ET

class LargestBoxTests(unittest.TestCase):
    def setUp(self):
        self.boxes1 = [[1, 1, 3, 3], [2, 2, 4, 4]]
        self.boxes2 = [[1, 1, 3, 3], [2, 2, 4, 4], [3, 0, 5, 2]]
    def test_one(self):
        box = gen_josm.largest_box(self.boxes1)
        self.assertEqual(['1', '1', '4', '4'], box)
    def test_two(self):
        box = gen_josm.largest_box(self.boxes2)
        self.assertEqual(['1', '0', '5', '4'], box)

class WaysTests(unittest.TestCase):
    def setUp(self):
        self.root = ET.parse('test.osm')
    def test_one(self):
        ways = gen_josm.make_ways(self.root)
        self.assertEqual(len(ways), 2)
        self.assertEqual(ways[0].get_bounds(), [-74.438181999999998, 40.484807000000004, -74.437437000000003, 40.485225])
        self.assertEqual(ways[1].get_bounds(), [-74.430002400000006, 40.476644999999998, -74.4297404, 40.478482])

class SubdivisionTests(unittest.TestCase):
    def setUp(self):
        self.root = ET.parse('test.osm')

if __name__ == '__main__':
    unittest.main()
