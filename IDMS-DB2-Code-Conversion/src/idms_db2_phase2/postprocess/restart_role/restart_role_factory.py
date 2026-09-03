from __future__ import annotations

from dataclasses import fields, is_dataclass

from idms_db2_phase2.postprocess.update_metadata_models import DclgenRoleInfo


class RestartRoleFactory:
    """Constructs DclgenRoleInfo while staying compatible with the model.

    Accepts the model's declared fields as kwargs and attaches any extra
    alias attributes after construction (best-effort).
    """

    def _make_role(self, **values: str) -> DclgenRoleInfo:
        if is_dataclass(DclgenRoleInfo):
            accepted = {field.name for field in fields(DclgenRoleInfo)}
            kwargs = {
                key: value for key, value in values.items() if key in accepted
            }
            role = DclgenRoleInfo(**kwargs)
        else:
            role = DclgenRoleInfo()

        for key, value in values.items():
            if not hasattr(role, key):
                try:
                    setattr(role, key, value)
                except Exception:
                    pass

        return role