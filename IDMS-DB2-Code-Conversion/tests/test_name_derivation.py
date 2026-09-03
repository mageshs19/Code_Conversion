from idms_db2_phase2.services.name_derivation_resolver import (
    NameDerivationResolver,
)


def _r():
    return NameDerivationResolver()


def test_program_id_with_site_char():
    # VM<site>BD<tail> -> VMDZ<site><tail>
    assert _r().derive("VM1BD567") == "VMDZ1567"


def test_record_name_without_site_char():
    # VMBD<tail> -> VMDZ<tail>
    assert _r().derive("VMBD205I") == "VMDZ205I"


def test_generic_vm_bd_name():
    assert _r().derive("VMBD510X") == "VMDZ510X"


def test_non_matching_name_unchanged():
    assert _r().derive("OPERATIES") == "OPERATIES"


def test_empty_and_none_safe():
    assert _r().derive("") == ""
    assert _r().derive(None) == ""


def test_is_derivable_flags():
    r = _r()
    assert r.is_derivable("VM1BD567") is True
    assert r.is_derivable("VMBD205I") is True
    assert r.is_derivable("OPERATIES") is False