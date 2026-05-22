def strip_ns(tag):
    return tag.split("}")[-1] if "}" in tag else tag