from lxml import etree as ET

def load_process(path):
    parser = ET.XMLParser(remove_blank_text=False)
    tree = ET.parse(path, parser)
    root = tree.getroot()
    return tree, root


def save_process(tree, path):
    tree.write(
        path,
        pretty_print=True,
        xml_declaration=True,
        encoding="utf-8"
    )
