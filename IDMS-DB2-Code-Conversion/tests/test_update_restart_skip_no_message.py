from idms_db2_phase2.composers.update_restart_skip_composer import (
    UpdateRestartSkipComposer,
)


def _fixed(body: str) -> str:
    return f"002690 {body[:65].ljust(65)} 02690000"


def test_manual_redesign_message_suppressed_by_default():
    text = "\n".join([
        _fixed("*DB2: UPDATE conversion skipped for FFRECAB."),
        _fixed("*DB2: Missing Sheet Mapping and DCLGEN metadata."),
        _fixed("CONTINUE."),
    ])
    composer = UpdateRestartSkipComposer()
    composer.compose(text)
    assert not any(
        "manual DB2 redesign" in m for m in composer.messages
    )


def test_message_flag_is_opt_in():
    composer = UpdateRestartSkipComposer()
    assert composer.EMIT_MANUAL_REDESIGN_MESSAGE is False