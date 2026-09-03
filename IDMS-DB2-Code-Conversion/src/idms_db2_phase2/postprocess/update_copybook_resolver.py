from __future__ import annotations

from typing import Any

from idms_db2_phase2.postprocess.update_metadata_models import (
    CobolFileInfo,
    CopybookRecordInfo,
    include_from_label,
    norm_name,
    upper,
    value,
)

from patterns.dynamic_metadata_patterns import PIC_LENGTH_RE


class UpdateCopybookResolver:
    def build_copybook_records(
        self,
        copybook_fields: list[Any],
    ) -> list[CopybookRecordInfo]:
        records: list[CopybookRecordInfo] = []
        current: CopybookRecordInfo | None = None

        for item in copybook_fields:
            level = self._field_level(item)
            name = norm_name(
                value(
                    item,
                    "name",
                    "field_name",
                    "cobol_name",
                    "copybook_field_name",
                    "field",
                )
            )

            if not name:
                continue

            source_label = upper(
                value(
                    item,
                    "source_label",
                    "copybook_name",
                    "source",
                    "file_name",
                    default="",
                )
            )

            if level == 1 or current is None:
                include_name = include_from_label(source_label) or name
                current = CopybookRecordInfo(
                    include_name=include_name,
                    record_name=name,
                    source_label=source_label,
                )
                records.append(current)

            current.fields.add(name)

            pic = value(item, "pic", "pic_clause", "picture", default="")
            occurs = value(item, "occurs", "occurs_times", default=1)

            try:
                occurs_count = int(occurs or 1)
            except (TypeError, ValueError):
                occurs_count = 1

            current.estimated_length += (
                self.estimate_pic_length(pic) * occurs_count
            )

        return records

    def choose_copybook(
        self,
        *,
        input_file: CobolFileInfo,
        copybooks: list[CopybookRecordInfo],
        copy_statements: set[str],
        source_refs: set[str],
    ) -> CopybookRecordInfo:
        if not copybooks:
            raise ValueError("No copybook fields were parsed from uploaded copybook input.")

        scored: list[tuple[int, CopybookRecordInfo]] = []

        read_target = norm_name(input_file.read_target)
        fd_record = norm_name(input_file.fd_record)

        for copybook in copybooks:
            score = 0

            if read_target and read_target in {
                copybook.record_name,
                copybook.include_name,
            }:
                score += 100

            if fd_record and fd_record in {
                copybook.record_name,
                copybook.include_name,
            }:
                score += 20

            if copybook.include_name in copy_statements:
                score += 50

            if copybook.record_name in copy_statements:
                score += 40

            if (
                input_file.record_length
                and copybook.estimated_length == input_file.record_length
            ):
                score += 30

            score += len(copybook.fields.intersection(source_refs))

            scored.append((score, copybook))

        scored.sort(key=lambda item: item[0], reverse=True)

        if scored[0][0] <= 0 and len(copybooks) > 1:
            raise ValueError(
                "Unable to resolve input copybook safely. "
                "Multiple copybooks exist and no reliable match was found."
            )

        return scored[0][1]

    def _field_level(
        self,
        item: Any,
    ) -> int:
        raw = value(
            item,
            "level",
            "level_number",
            "cobol_level",
            default=0,
        )

        try:
            return int(raw)
        except (TypeError, ValueError):
            return 0

    def estimate_pic_length(
        self,
        pic: Any,
    ) -> int:
        text = upper(pic)

        if not text:
            return 0

        text = text.replace(" ", "").replace(".", "")
        digits = 0

        for match in PIC_LENGTH_RE.finditer(text):
            digits += int(match.group(1)) if match.group(1) else 1

        if "COMP-3" in text or "COMP_3" in text:
            return int((digits + 2) / 2)

        return digits