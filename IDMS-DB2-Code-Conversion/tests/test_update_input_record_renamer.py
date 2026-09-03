from idms_db2_phase2.postprocess.update_input_record_renamer import (
    UpdateInputRecordRenamer,
)


def _fixed(body: str, seq: str = "000750") -> str:
    return f"{seq} {body[:65].ljust(65)} 00750000"


def _comment(body: str, seq: str = "000260") -> str:
    # Column 7 = '*' comment indicator.
    return f"{seq}*{body[:65].ljust(65)} 00260000"


def test_executable_references_renamed():
    block = "\n".join([
        _fixed("COPY VMBD205I."),
        _fixed("INITIALIZE VMBD205I."),
        _fixed("READ OPERATIES INTO VMBD205I"),
        _fixed("MOVE NR-ID-FORM-AS OF VMBD205I"),
    ])
    out = UpdateInputRecordRenamer().apply(
        block, old_name="VMBD205I", new_name="VMDZ205I"
    )
    assert "VMBD205I" not in out
    assert "COPY VMDZ205I" in out
    assert "INITIALIZE VMDZ205I" in out
    assert "OF VMDZ205I" in out


def test_comment_line_preserved():
    block = "\n".join([
        _comment("DAISY SECURITIES KASBONS : VMBD510X --> VMBD205I"),
        _fixed("COPY VMBD205I."),
    ])
    out = UpdateInputRecordRenamer().apply(
        block, old_name="VMBD205I", new_name="VMDZ205I"
    )
    # The comment (historical REMARKS) must keep the original VMBD205I.
    assert "VMBD205I  --" in out or "VMBD205I" in out.splitlines()[0]
    # But the executable COPY must be renamed.
    assert "COPY VMDZ205I" in out


def test_duplicate_copy_deduplicated():
    block = "\n".join([
        _fixed("COPY VMBD205I.", seq="000750"),
        _fixed("COPY VMDZ205I.", seq="001680"),
    ])
    out = UpdateInputRecordRenamer().apply(
        block, old_name="VMBD205I", new_name="VMDZ205I"
    )
    # After renaming the first COPY to VMDZ205I, only ONE COPY VMDZ205I remains.
    assert out.upper().count("COPY VMDZ205I") == 1


def test_no_change_when_old_equals_new():
    block = _fixed("COPY VMDZ205I.")
    out = UpdateInputRecordRenamer().apply(
        block, old_name="VMDZ205I", new_name="VMDZ205I"
    )
    assert "COPY VMDZ205I" in out