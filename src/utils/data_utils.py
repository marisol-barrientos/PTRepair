import re

def parse_data_access(input_string):
    if input_string is None:
        return {}

    data_dict = {}

    data_accesses = re.findall(r"data\.([a-zA-Z_]\w*)", input_string)

    for key in data_accesses:
        pattern = rf"data\.{key}\s*=\s*(.+)"
        match = re.search(pattern, input_string)

        if match:
            value = match.group(1).strip()
            data_dict[key] = value
        else:
            data_dict[key] = key

    return data_dict