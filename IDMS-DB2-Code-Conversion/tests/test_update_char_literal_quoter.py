from idms_db2_phase2.postprocess.update_final_cleanup import UpdateFinalCleanup


def _fixed(body: str) -> str:
    """Build an 80-col fixed-format line: left(6)+space+body(65)+space+right(8)."""
    return f"002430 {body[:65].ljust(65)} 02430000"


def test_non_sql_move_dot_reference_is_rewritten_to_of():
    line = _fixed("MOVE DA-DD-MM-CCYY TO DCLDZBFARTV.DA-INFSDGD-479BFAR")
    out = UpdateFinalCleanup().apply(line)
    assert "DA-INFSDGD-479BFAR OF DCLDZBFARTV" in out
    assert "DCLDZBFARTV.DA-INFSDGD" not in out


def test_one_line_exec_sql_include_does_not_wedge_flag():
    # A one-line EXEC SQL INCLUDE must NOT cause a later non-SQL dot-reference
    # line to be treated as inside EXEC SQL (the wedge regression).
    include = _fixed("EXEC SQL INCLUDE DZBFARTV END-EXEC.")
    move = _fixed("MOVE DA-DD-MM-CCYY TO DCLDZBFARTV.DA-INFSDGD-479BFAR")
    out = UpdateFinalCleanup().apply(include + "\n" + move)
    assert "DA-INFSDGD-479BFAR OF DCLDZBFARTV" in out
    assert "DCLDZBFARTV.DA-INFSDGD" not in out


def test_sql_host_reference_inside_exec_sql_preserved():
    block = "\n".join([
        _fixed("EXEC SQL"),
        _fixed("UPDATE DZBFARTV"),
        _fixed("SET"),
        _fixed("DA_INFSDGD_479BFAR = :DCLDZBFARTV.DA-INFSDGD-479BFAR"),
        _fixed("END-EXEC."),
    ])
    out = UpdateFinalCleanup().apply(block)
    # SQL host var must stay in :DCLGROUP.FIELD form.
    assert ":DCLDZBFARTV.DA-INFSDGD-479BFAR" in out