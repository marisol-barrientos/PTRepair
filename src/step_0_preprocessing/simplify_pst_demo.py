import argparse
import json
from pathlib import Path
from typing import Union

try:
    # Used when imported as part of the package.
    from .utils.xml_loader import load_xml
    from .converter.cpee_to_simplified_pst import convert
    from .utils.exporter import pst_to_dict, pst_to_text
except ImportError:
    # Used when this file is executed directly.
    from utils.xml_loader import load_xml
    from converter.cpee_to_simplified_pst import convert
    from utils.exporter import pst_to_dict, pst_to_text


PathLike = Union[str, Path]


def simplify_pst(original_pst_file: PathLike) -> str:
    """
    Convert an original XML process model into a simplified PST.

    The simplified PST is returned as text and is not written to disk.

    Parameters
    ----------
    original_pst_file : str | Path
        Path to the original XML process model.

    Returns
    -------
    str
        Simplified PST represented as text.

    Raises
    ------
    FileNotFoundError
        If the original XML file does not exist.

    ValueError
        If the provided input is not an XML file or the generated PST is empty.
    """

    xml_file = Path(original_pst_file).expanduser().resolve()

    if not xml_file.exists():
        raise FileNotFoundError(
            f"Original process model not found: {xml_file}"
        )

    if not xml_file.is_file():
        raise ValueError(
            f"Original process model is not a file: {xml_file}"
        )

    if xml_file.suffix.lower() != ".xml":
        raise ValueError(
            f"Expected an XML process model, received: {xml_file.name}"
        )

    # Parse the original XML process model.
    root = load_xml(xml_file)

    # Convert the original model into the internal simplified PST.
    pst = convert(root)

    # Convert the PST into the text representation expected by the LLM.
    pst_text = pst_to_text(pst).strip()

    if not pst_text:
        raise ValueError(
            f"The simplified PST generated from {xml_file} is empty."
        )

    # Preserve the previous behavior of ending the PST with "terminate".
    if not pst_text.endswith("terminate"):
        pst_text = f"{pst_text}\nterminate"

    return pst_text


def simplify_pst_as_dict(original_pst_file: PathLike) -> dict:
    """
    Convert an original XML process model into a simplified PST dictionary.

    This function is optional and can be useful for debugging or other
    processing steps.

    Parameters
    ----------
    original_pst_file : str | Path
        Path to the original XML process model.

    Returns
    -------
    dict
        Simplified PST represented as a dictionary.
    """

    xml_file = Path(original_pst_file).expanduser().resolve()

    if not xml_file.exists():
        raise FileNotFoundError(
            f"Original process model not found: {xml_file}"
        )

    if not xml_file.is_file():
        raise ValueError(
            f"Original process model is not a file: {xml_file}"
        )

    root = load_xml(xml_file)
    pst = convert(root)

    return pst_to_dict(pst)


def main() -> None:
    """
    Optional command-line interface for testing the simplifier.

    Running this file directly prints the simplified PST. It only writes an
    output file when --output is explicitly supplied.
    """

    parser = argparse.ArgumentParser(
        description=(
            "Convert an original XML process model into a simplified PST."
        )
    )

    parser.add_argument(
        "input",
        type=Path,
        help="Path to the original XML process model.",
    )

    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help=(
            "Optional output file. When omitted, the simplified PST is only "
            "printed and is not saved."
        ),
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the simplified PST dictionary for debugging.",
    )

    args = parser.parse_args()

    simplified_pst = simplify_pst(args.input)

    print("\n=== Simplified PST ===")
    print(simplified_pst)

    if args.json:
        simplified_dict = simplify_pst_as_dict(args.input)

        print("\n=== Simplified PST JSON ===")
        print(
            json.dumps(
                simplified_dict,
                indent=2,
                ensure_ascii=False,
            )
        )

    if args.output is not None:
        output_file = args.output.expanduser().resolve()
        output_file.parent.mkdir(parents=True, exist_ok=True)

        output_file.write_text(
            simplified_pst,
            encoding="utf-8",
        )

        print(f"\nSimplified PST saved to: {output_file}")


if __name__ == "__main__":
    main()