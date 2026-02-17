#!/usr/bin/env python3

# Copyright (c) 2026 Remi Locherer <remi@arista.com>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""
Convert exported CloudVision static confglets (ZIP file containing a JSON
file or just the JSON file) to a YAML file that can be imported into the 
"Static Configuration" studio.
"""

from __future__ import annotations

import json
import yaml
import hashlib
import sys
import zipfile
import logging
import re
import argparse
from pathlib import Path
from typing import Any, Dict, List

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def multiline_str_representer(dumper: yaml.SafeDumper, data: str):
    """Represent multiline strings with literal block style '|'."""
    style = "|" if "\n" in data else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)

# Register the representer for all strings
yaml.add_representer(str, multiline_str_representer, Dumper=yaml.SafeDumper)

def generate_digest(text: str) -> str:
    """Generate a SHA-256 hex digest of the given text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

class ConversionError(Exception):
    """Raised for non-IO conversion errors."""

def _select_zip_member(z: zipfile.ZipFile) -> str:
    """Select the first JSON file or non-directory file from the zip."""
    names = [info.filename for info in z.infolist() if not info.is_dir()]
    if not names:
        raise ConversionError("Zip archive contains no files.")
    for n in names:
        if n.lower().endswith(".json"):
            return n
    return names[0]

def convert_configlets(input_file: str, output_file: str | None = None, *, overwrite: bool = False) -> tuple[Path, int, int]:
    """
    Convert the given input file to YAML.
    Returns: (output_path, success_count, skip_count)
    """
    input_path = Path(input_file)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    output_path = Path(output_file) if output_file else input_path.with_suffix(".yaml")

    if output_path.exists() and not overwrite:
        raise ConversionError(f"Output file {output_path} already exists (use --overwrite to replace).")

    content = ""
    if zipfile.is_zipfile(input_path):
        with zipfile.ZipFile(input_path, "r") as z:
            member_name = _select_zip_member(z)
            logging.info("Reading '%s' from archive '%s'.", member_name, input_path.name)
            with z.open(member_name) as f:
                raw = f.read()
                try:
                    content = raw.decode("utf-8")
                except UnicodeDecodeError:
                    content = raw.decode("utf-8", errors="replace")
    else:
        content = input_path.read_text(encoding="utf-8", errors="replace")

    json_data: Dict[str, Any] = json.loads(content)

    data_section = json_data.get("data")
    if not isinstance(data_section, dict):
        raise ConversionError("JSON top-level 'data' key missing or not an object.")
    
    raw_configlets = data_section.get("configlet")
    if not isinstance(raw_configlets, list):
        raise ConversionError("JSON 'data.configlet' missing or not a list.")

    configlets_list: List[Dict[str, Any]] = []
    success_count = 0
    skip_count = 0

    for idx, item in enumerate(raw_configlets):
        if not isinstance(item, dict) or "config" not in item or "key" not in item:
            logging.warning("Skipping malformed entry at index %d.", idx)
            skip_count += 1
            continue

        # Body: Replace escaped \n with actual newlines
        body = item.get("config", "")
        if isinstance(body, str):
            body = body.replace("\\n", "\n")
            if body.strip():
                body = body.rstrip() + "\n"
        else:
            body = str(body)

        # ID: Extract UUID after 'configlet_'
        key_val = item.get("key", "")
        config_id = key_val.split("_")[-1] if "_" in key_val else key_val

        # Timestamp: Convert dateTimeInLongFormat
        millis = item.get("dateTimeInLongFormat", 0)
        try:
            millis_int = int(millis)
        except (TypeError, ValueError):
            millis_int = 0

        yaml_entry: Dict[str, Any] = {
            "configletId": config_id,
            "digest": generate_digest(body),
            "description": item.get("note", "") or "",
            "displayName": item.get("name", "") or "",
            "migratedFrom": "",
            "body": body,
            "lastModifiedAt": {
                "seconds": str(millis_int // 1000),
                "nanos": (millis_int % 1000) * 1_000_000,
            },
            "lastModifiedBy": item.get("user", "") or "",
            "size": str(len(body)),
        }
        configlets_list.append(yaml_entry)
        success_count += 1

    final_output = {"path": [], "inputs": {"configlets": configlets_list}}

    yaml_text = yaml.safe_dump(final_output, sort_keys=False, default_flow_style=False)
    output_path.write_text(yaml_text, encoding="utf-8")
    return output_path, success_count, skip_count

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert CloudVision static configlet export to Static Config Studio YAML."
    )
    parser.add_argument("input", help="Input JSON or ZIP file")
    parser.add_argument("output", nargs="?", help="Optional output YAML path")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output file")

    args = parser.parse_args()

    try:
        out_path, success, skipped = convert_configlets(args.input, output_file=args.output, overwrite=args.overwrite)
        
        # Final Summary Output
        print("-" * 30)
        print("Conversion Summary:")
        print(f"  Successfully Converted: {success}")
        print(f"  Skipped Malformed:      {skipped}")
        print(f"  Output File:            {out_path}")
        print("-" * 30)
        
        return 0
    except (FileNotFoundError, json.JSONDecodeError, ConversionError) as e:
        logging.error(str(e))
    except Exception:
        logging.exception("Unexpected error during conversion.")
    return 1

if __name__ == "__main__":
    sys.exit(main())