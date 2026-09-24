# LOCATION: src/idms_db2_phase2/repositories/lrf_repository.py
# ACTION: CREATE NEW FILE
"""Read-only lookups over parsed LRF metadata."""

from __future__ import annotations

from idms_db2_phase2.domain.models import LogicalRecord, LrfPath
from idms_db2_phase2.services.name_normalizer import NameNormalizer
from rules.lrf_rules import PATH_GROUP_ERASE, PATH_GROUP_OBTAIN


class LrfRepository:
    def __init__(self, logical_records: list[LogicalRecord] | None = None) -> None:
        self._records = list(logical_records or [])
        self._by_name = {
            NameNormalizer.normalize(r.logical_record_name): r
            for r in self._records
        }

    def is_empty(self) -> bool:
        return not self._records

    def names(self) -> list[str]:
        return [r.logical_record_name for r in self._records]

    def get(self, logical_record_name: str) -> LogicalRecord | None:
        return self._by_name.get(NameNormalizer.normalize(logical_record_name))

    def element_records(self, logical_record_name: str) -> list[str]:
        record = self.get(logical_record_name)
        return list(record.element_records) if record else []

    def path_for_keyword(self, keyword: str) -> LrfPath | None:
        wanted = NameNormalizer.normalize(keyword)
        for record in self._records:
            for path in record.paths:
                if NameNormalizer.normalize(path.keyword) == wanted:
                    return path
        return None

    def obtain_paths(self, logical_record_name: str) -> list[LrfPath]:
        return self._paths(logical_record_name, PATH_GROUP_OBTAIN)

    def erase_paths(self, logical_record_name: str) -> list[LrfPath]:
        return self._paths(logical_record_name, PATH_GROUP_ERASE)

    def owns_record(self, record_name: str) -> list[str]:
        """Which logical records include this IDMS record as an element."""
        wanted = NameNormalizer.normalize(record_name)
        return [
            r.logical_record_name
            for r in self._records
            if any(NameNormalizer.normalize(e) == wanted for e in r.element_records)
        ]

    def _paths(self, logical_record_name: str, verb: str) -> list[LrfPath]:
        record = self.get(logical_record_name)
        if not record:
            return []
        return [p for p in record.paths if p.path_group_verb == verb]