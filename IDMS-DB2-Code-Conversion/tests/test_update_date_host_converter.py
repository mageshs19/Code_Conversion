from types import SimpleNamespace

from idms_db2_phase2.postprocess.update_date_host_converter import (
    UpdateDateHostConverter,
)


def _col(host, db2_type):
    return SimpleNamespace(
        cobol_host_name=host,
        db2_type=db2_type,
        cobol_picture="",
        column_name="",
        table_name="DZBFARTV",
    )


def _fixed(body: str) -> str:
    return f"002300 {body[:65].ljust(65)} 02300000"


def _converter():
    cols = [
        _col("DA-CRFMAS-479BFAR", "DATE NOT NULL"),
        _col("DA-INFSDGD-479BFAR", "DATE NOT NULL"),
        _col("TS-UPDATE-479BFAR", "TIMESTAMP NOT NULL"),
        _col("ID-USERID-479BFAR", "CHAR(8) NOT NULL"),
    ]
    return UpdateDateHostConverter(cols)


def test_raw_move_to_date_host_is_converted_one_line():
    line = _fixed("MOVE DA-CREA-FORM-AS-R TO DA-CRFMAS-479BFAR OF DCLDZBFARTV")
    out = _converter().apply(line)
    assert "MOVE ZEROES TO DA-CCYYMMDD" in out
    assert "MOVE DA-CREA-FORM-AS-R TO DA-CCYYMMDD" in out
    assert "MOVE 00010101 TO DA-CCYYMMDD" in out
    assert "MOVE CORR DA-CCYYMMDD-R TO DA-DD-MM-CCYY" in out
    assert "MOVE DA-DD-MM-CCYY TO DA-CRFMAS-479BFAR OF DCLDZBFARTV" in out
    # The raw direct move must be gone.
    assert "MOVE DA-CREA-FORM-AS-R TO DA-CRFMAS-479BFAR" not in out


def test_raw_move_to_date_host_is_converted_wrapped():
    block = "\n".join([
        _fixed("MOVE DA-CREA-FORM-AS-R"),
        _fixed("TO DA-CRFMAS-479BFAR OF DCLDZBFARTV"),
    ])
    out = _converter().apply(block)
    assert "MOVE DA-DD-MM-CCYY TO DA-CRFMAS-479BFAR OF DCLDZBFARTV" in out


def test_timestamp_audit_move_is_never_converted():
    # REGRESSION GUARD: a TIMESTAMP host receiving TS-TIMESTAMP must stay raw.
    line = _fixed("MOVE TS-TIMESTAMP TO TS-UPDATE-479BFAR OF DCLDZBFARTV")
    out = _converter().apply(line)
    assert "MOVE TS-TIMESTAMP TO TS-UPDATE-479BFAR OF DCLDZBFARTV" in out
    assert "MOVE DA-DD-MM-CCYY TO TS-UPDATE-479BFAR" not in out
    assert "MOVE ZEROES TO DA-CCYYMMDD" not in out


def test_user_audit_char_move_is_never_converted():
    line = _fixed("MOVE CS-PROGRAM TO ID-USERID-479BFAR OF DCLDZBFARTV")
    out = _converter().apply(line)
    assert "MOVE CS-PROGRAM TO ID-USERID-479BFAR OF DCLDZBFARTV" in out
    assert "MOVE DA-DD-MM-CCYY TO ID-USERID-479BFAR" not in out


def test_exec_sql_host_reference_untouched():
    block = "\n".join([
        _fixed("EXEC SQL"),
        _fixed("UPDATE DZBFARTV"),
        _fixed("SET DA_CRFMAS_479BFAR = :DCLDZBFARTV.DA-CRFMAS-479BFAR"),
        _fixed("END-EXEC."),
    ])
    out = _converter().apply(block)
    assert ":DCLDZBFARTV.DA-CRFMAS-479BFAR" in out
    assert "MOVE ZEROES TO DA-CCYYMMDD" not in out
