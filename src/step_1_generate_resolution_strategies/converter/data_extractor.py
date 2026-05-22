import re

NAMESPACE = {"ns0": "http://cpee.org/ns/description/1.0"}


def extract_data_from_call(call):
    read = set()
    write = set()

    # --- PREPARE ---
    prepare = call.find(".//ns0:prepare", NAMESPACE)
    if prepare is not None and prepare.text:
        read.update(extract_data_access(prepare.text))

    # --- ARGUMENTS ---
    arguments = call.find(".//ns0:arguments", NAMESPACE)
    if arguments is not None:
        for child in arguments:
            if child.text:
                read.update(extract_data_access(child.text))

    # --- FINALIZE ---
    finalize = call.find(".//ns0:finalize", NAMESPACE)
    if finalize is not None and finalize.text:
        writes = extract_data_writes(finalize.text)
        write.update(writes)

    return {
        "read": sorted(read),
        "write": sorted(write)
    }

def extract_data_access(text):
    """
    Extract all data.<x> occurrences (reads)
    """
    if not text:
        return []

    matches = re.findall(r"data\.([a-zA-Z_]\w*)", text)
    return matches


def extract_data_writes(text):
    """
    Extract assignments: data.x = ...
    """
    if not text:
        return []

    matches = re.findall(r"data\.([a-zA-Z_]\w*)\s*=", text)
    return matches