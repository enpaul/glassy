"""Main program entrypoint and CLI interface"""

import argparse
import sys
from pathlib import Path

from glassy import __about__


def get_args() -> argparse.Namespace:
    """Parse the CLI arguments"""

    parser = argparse.ArgumentParser(prog=__about__.__title__, description=__about__.__summary__)

    parser.add_argument("--version", help="Show program version and exit", action="store_true")
    parser.add_argument("-c", "--config", help="Path to the program config file", default=Path("~", ".config", "glassy.yaml").resolve())
    parser.add_argument("--check", help="Check syntax of the config file and diagram without running network tests", action="store_true")
    parser.add_argument("-o", "--output", help="Path to a file to output the rendered result, or one of the magic values 'stdout' or 'stderr'", default="stdout")
    parser.add_argument("template", help="Path to the template diagram to render and output")

    return parser.parse_args()
    

def main() -> int:
    args = get_args()

    if args.version:
        print(f"{__about__.__title__} {__about__.__version__}", file=sys.stderr)
        return 0


    return 0


if __name__ == "__main__":
    sys.exit(main())