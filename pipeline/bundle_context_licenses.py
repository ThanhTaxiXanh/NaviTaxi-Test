#!/usr/bin/env python3
"""Include required LGPL source notices with quarantine GIS artifacts."""
import argparse
from importlib import metadata
from pathlib import Path
import shutil


def bundle(output_dir: Path) -> list[Path]:
    dist = metadata.distribution("basemap-data")
    if dist.version != "2.0.0":
        raise ValueError("Unpinned basemap-data source")
    output_dir.mkdir(parents=True, exist_ok=True)
    copied = []
    for record in dist.files or []:
        filename = str(record)
        if filename.endswith(("licenses/COPYING", "licenses/COPYING.LESSER")):
            source = dist.locate_file(record)
            target = output_dir / Path(filename).name
            shutil.copyfile(source, target)
            copied.append(target)
    if {file.name for file in copied} != {"COPYING", "COPYING.LESSER"}:
        raise ValueError("Required LGPL notices missing; artifact blocked")
    return copied


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    files = bundle(parser.parse_args().output_dir)
    print("Included LGPL notices:", *(p.name for p in files))


if __name__ == "__main__":
    main()
