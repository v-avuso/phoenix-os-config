"""Always use the native picker; default Hue's remember checkbox to checked."""
import argparse
import os
from sources import picker_arguments


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--picker", required=True)
    args, forwarded = parser.parse_known_args()
    arguments = picker_arguments(os.environ.get("XDPH_APP_ID", ""), forwarded)
    os.execv(args.picker, [args.picker, *arguments])


if __name__ == "__main__":
    main()
