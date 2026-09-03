from __future__ import annotations

import re
from pathlib import Path


def build_converted_cobol_file_name(
    target_program_id: str,
    source_file_name: str,
) -> str:
    target_stem = sanitize_file_stem(target_program_id)

    if target_stem:
        return f"{target_stem}_db2.cbl"

    source_name = str(source_file_name or "").strip()

    if source_name:
        source_stem = sanitize_file_stem(Path(source_name).stem)

        if source_stem:
            return f"{source_stem}_db2.cbl"

    return "converted_db2_cobol.cbl"


def sanitize_file_stem(value: str) -> str:
    text = str(value or "").strip()

    if not text:
        return ""

    text = re.sub(r"[^A-Za-z0-9_-]+", "_", text)
    text = re.sub(r"_+", "_", text)

    return text.strip("_")