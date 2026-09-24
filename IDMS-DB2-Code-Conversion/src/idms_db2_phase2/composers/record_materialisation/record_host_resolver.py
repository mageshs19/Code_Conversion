# LOCATION: src/idms_db2_phase2/composers/record_materialisation/record_host_resolver.py
# ACTION: CREATE NEW FILE
"""Adapter over the table and host-variable resolvers.

DCLGEN is the authority for host variable spelling. This class does not
decide whether a lookup SHOULD happen - it only performs one and
normalises the answer. Every method is total: a resolver that raises
yields an empty string, so one bad column can never abort the pass.
"""

from __future__ import annotations

HOST_PREFIX = ":"
GROUP_SEPARATOR = "."
HOST_OF_GROUP_TEMPLATE = "{host} OF {group}"


class RecordHostResolver:
    """Resolves record -> table -> DCLGEN group -> host reference."""

    def __init__(
        self,
        *,
        table_name_resolver,
        host_variable_resolver,
    ) -> None:
        self.table_name_resolver = table_name_resolver
        self.host_variable_resolver = host_variable_resolver

    # ------------------------------------------------------------ table
    def table_for(self, record: str) -> str:
        if not record:
            return ""
        try:
            return str(
                self.table_name_resolver.table_for_record(record) or ""
            )
        except Exception:  # noqa: BLE001
            return ""

    # ------------------------------------------------------------ group
    def group_for(self, table: str) -> str:
        if not table:
            return ""
        try:
            return str(
                self.host_variable_resolver.group_for_table(table) or ""
            )
        except Exception:  # noqa: BLE001
            return ""

    # ------------------------------------------------------------- host
    def host_for(self, table: str, column: str) -> str:
        """'DA-CRFMAS-479BFAS OF DCLDZBFASTV', or '' when unresolved.

        DCLGEN resolvers report a host either as ':GROUP.HOST' or as a
        bare name. Both are normalised to the qualified COBOL form the
        generated MOVE needs.
        """
        if not table or not column:
            return ""

        try:
            reference = self.host_variable_resolver.host_reference_for_column(
                table_name=table,
                column_name=column,
            )
        except Exception:  # noqa: BLE001
            return ""

        return self.normalize(reference)

    # --------------------------------------------------------- helpers
    @staticmethod
    def normalize(reference) -> str:
        text = str(reference or "").strip().lstrip(HOST_PREFIX)
        if not text:
            return ""

        if GROUP_SEPARATOR in text:
            group, _sep, host = text.partition(GROUP_SEPARATOR)
            return HOST_OF_GROUP_TEMPLATE.format(
                host=host.strip().upper(),
                group=group.strip().upper(),
            )

        return text.upper()


__all__ = ["RecordHostResolver"]