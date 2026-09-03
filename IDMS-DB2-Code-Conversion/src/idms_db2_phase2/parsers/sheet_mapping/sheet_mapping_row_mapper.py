from __future__ import annotations

from catalogs.sheet_mapping_schema import (
    SHEET_MAPPING_CANONICAL_COLUMNS,
    SHEET_MAPPING_FIELD_ALIASES,
    SHEET_MAPPING_HEADER_DETECTION_GROUPS,
    SHEET_MAPPING_MODEL_FIELD_MAP,
)
from idms_db2_phase2.domain.models import SheetMappingRow
from rules.sheet_mapping_parser_rules import (
    DIAG_SHEET_NORMALIZED_CELLS_TEMPLATE,
    HEADER_DEBUG_ROW_LIMIT,
    HEADER_SCAN_ROW_LIMIT,
)


class SheetMappingRowMapper:
    """Header detection, row-to-dict, and dict-to-model mapping.

    Column names, aliases, and detection groups come from
    catalogs/sheet_mapping_schema.py.
    """

    def _row_to_dict(self, headers: list[str], row: tuple) -> dict[str, str]:
        raw_row: dict[str, str] = {}
        for index, header in enumerate(headers):
            clean_header = self._cell_to_string(header)
            if not clean_header:
                continue
            value = row[index] if index < len(row) else ""
            raw_row[clean_header] = self._cell_to_string(value)
        return raw_row

    def _find_header_row(self, rows: list[tuple], sheet_title: str) -> int:
        first_canonical = self._normalize_header(SHEET_MAPPING_CANONICAL_COLUMNS[0])

        for index, row in enumerate(rows[:HEADER_SCAN_ROW_LIMIT]):
            normalized_cells = {
                self._normalize_header(self._cell_to_string(value))
                for value in row
                if value is not None
            }

            if index < HEADER_DEBUG_ROW_LIMIT:
                self.diagnostics.append(
                    DIAG_SHEET_NORMALIZED_CELLS_TEMPLATE.format(
                        sheet=sheet_title,
                        index=index,
                        cells=sorted(normalized_cells),
                    )
                )

            if first_canonical in normalized_cells:
                return index

            if self._row_has_any_header(
                normalized_cells=normalized_cells,
                aliases=SHEET_MAPPING_HEADER_DETECTION_GROUPS[0],
            ):
                return index

            if self._row_has_any_header(
                normalized_cells=normalized_cells,
                aliases=SHEET_MAPPING_HEADER_DETECTION_GROUPS[1],
            ) and self._row_has_any_header(
                normalized_cells=normalized_cells,
                aliases=SHEET_MAPPING_HEADER_DETECTION_GROUPS[2],
            ):
                return index

        return -1

    def _row_has_any_header(
        self, normalized_cells: set[str], aliases: list[str]
    ) -> bool:
        return any(
            self._normalize_header(alias) in normalized_cells for alias in aliases
        )

    def _to_mapping_row(self, raw_row: dict[str, str]) -> SheetMappingRow:
        values = {
            model_field: self._get(row=raw_row, canonical_name=canonical_column)
            for model_field, canonical_column in SHEET_MAPPING_MODEL_FIELD_MAP.items()
        }
        return SheetMappingRow(**values)

    def _get(self, row: dict[str, str], canonical_name: str) -> str:
        aliases = SHEET_MAPPING_FIELD_ALIASES.get(canonical_name, [canonical_name])
        normalized_lookup = {
            self._normalize_header(key): value for key, value in row.items()
        }
        for alias in aliases:
            value = normalized_lookup.get(self._normalize_header(alias))
            if value is not None:
                return str(value).strip()
        return ""

    def _has_useful_content(self, row: SheetMappingRow) -> bool:
        return any(
            str(getattr(row, field_name) or "").strip()
            for field_name in SHEET_MAPPING_MODEL_FIELD_MAP
        )