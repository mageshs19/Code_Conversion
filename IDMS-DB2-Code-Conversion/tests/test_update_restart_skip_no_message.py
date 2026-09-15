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


# --- Manual-redesign diagnostic --------------------------------------
#
# When a restart or control record has no usable Sheet Mapping entry,
# UpdateRestartSkipComposer replaces the generated block with a
# manual-redesign comment and CONTINUE. That replacement is visible in
# the generated COBOL and is the authoritative signal.
#
# Emitting a matching VALIDATION MESSAGE as well is opt-in, because it
# repeats on every run for a condition that is an input-data gap rather
# than a converter defect, and drowns out genuine diagnostics.
#
# Consumed by:
#   src/idms_db2_phase2/composers/update_restart_skip_composer.py
#
# Mirrored onto the composer as a class attribute so callers and tests
# read it from one place and the two cannot drift apart.
EMIT_MANUAL_REDESIGN_MESSAGE = False

MANUAL_REDESIGN_MESSAGE_TEMPLATE = (
    "Update restart skip: {record} has no usable Sheet Mapping entry; "
    "block replaced with a manual-redesign comment."
)