import xml.etree.ElementTree as ET


def load_xml(path):
    tree = ET.parse(path)
    return tree.getroot()