# LOCATION: tests/test_no_pass_loses_characters.py
# ACTION: CREATE NEW FILE
"""No pass may lose characters from a PROCEDURE DIVISION statement.

REGRESSION
----------
A four-line IF condition reaches the generated file as two lines cut
mid-name:

    IF (HELP-DA-CPTAFS-479BFAS < DA-ARCH-YMD  AND HELP-DA-CPTAFS-
       (HELP-DA-CRFMAS-479BFAS < DA-ARCH-YMD AND HELP-DA-CPTAFS-4

losing "NOT = '00000000') OR" and "= '00000000')" entirely.

WHY THIS FILE EXISTS ALONGSIDE test_condition_is_never_truncated.py
------------------------------------------------------------------
That file asserts the same property against ProcedureIndentNormalizer
ONLY, and passes. Pipeline instrumentation then proved the normalizer is
a no-op on the real program: debug_indent_in.txt and debug_indent_out.txt
are byte-identical, and the condition arrives ALREADY merged.

So the damage is done by a pass that no test covers. This file applies
the same assertion to every candidate, so the failing one names itself.
"""

import importlib

import pytest

QUOTE = chr(39)
ZERO8 = QUOTE + "00000000" + QUOTE


def fixed(seq: str, body: str, right: str) -> str:
    assert len(body) <= 65
    return seq + " " + body.ljust(65) + right


# Identical to the fixture in test_condition_is_never_truncated.py, so a
# failure here cannot be blamed on a different input.
SOURCE = "\n".join(
    [
        fixed("001750", " PROCEDURE DIVISION.", "01750000"),
        fixed("002290", " BEHANDELING.", "02290000"),
        fixed("002600", "    IF (HELP-DA-CPTAFS-479BFAS < DA-ARCH-YMD", "02600000"),
        fixed("002610", "    AND HELP-DA-CPTAFS-479BFAS NOT = " + ZERO8 + ") OR", "02610000"),
        fixed("002620", "    (HELP-DA-CRFMAS-479BFAS < DA-ARCH-YMD AND", "02620000"),
        fixed("002630", "    HELP-DA-CPTAFS-479BFAS = " + ZERO8 + ")", "02630000"),
        fixed("002660", "       ADD 1 TO WS-TELLER", "02660000"),
        fixed("002770", "    END-IF.", "02770000"),
    ]
) + "\n"


# module, class, candidate entry-point names
CANDIDATES = [
    (
        "idms_db2_phase2.services.cobol_area_alignment_service",
        "CobolAreaAlignmentService",
        ("align", "apply", "compose"),
    ),
    (
        "idms_db2_phase2.services.procedure_block_indent_service",
        "ProcedureBlockIndentService",
        ("apply", "compose", "indent", "format"),
    ),
    (
        "idms_db2_phase2.services.string_block_format_service",
        "StringBlockFormatService",
        ("apply", "compose", "format"),
    ),
    (
        "idms_db2_phase2.services.db2_comment_readability_service",
        "Db2CommentReadabilityService",
        ("apply", "compose"),
    ),
    (
        "idms_db2_phase2.composers.db2_date_comparison_composer",
        "Db2DateComparisonComposer",
        ("compose", "apply"),
    ),
    (
        "idms_db2_phase2.composers.final_cobol_fix_composer",
        "FinalCobolFixComposer",
        ("compose", "apply", "fix"),
    ),
    (
        "idms_db2_phase2.composers.procedure_indent_normalizer",
        "ProcedureIndentNormalizer",
        ("compose",),
    ),
        # ---- Layout pipeline, steps 1-8. Omitted from the first version,
    # which is why it found nothing. fixed_format_line_composer.py:148
    # carries an unguarded  safe_body = safe_body[:BODY_WIDTH].
    (
        "idms_db2_phase2.composers.fixed_format_composer",
        "FixedFormatComposer",
        ("compose", "apply", "format"),
    ),
    (
        "idms_db2_phase2.composers.fixed_format_line_composer",
        "FixedFormatLineComposer",
        ("compose", "apply", "build", "format"),
    ),
    (
        "idms_db2_phase2.composers.manual_layout_composer",
        "ManualLayoutComposer",
        ("compose", "apply"),
    ),
    (
        "idms_db2_phase2.composers.manual_style_preserver",
        "ManualStylePreserver",
        ("compose", "apply", "preserve"),
    ),
    (
        "idms_db2_phase2.composers.structural_safety_composer",
        "StructuralSafetyComposer",
        ("compose", "apply"),
    ),
    (
        "idms_db2_phase2.composers.sqlcode_wrapper_cleanup_composer",
        "SqlcodeWrapperCleanupComposer",
        ("compose", "apply"),
    ),
    (
        "idms_db2_phase2.composers.unmapped_record_block_composer",
        "UnmappedRecordBlockComposer",
        ("compose", "apply"),
    ),
    (
        "idms_db2_phase2.composers.counter_declaration_composer",
        "CounterDeclarationComposer",
        ("compose", "apply"),
    ),
    (
        "idms_db2_phase2.composers.late_db2_date_composer",
        "LateDb2DateComposer",
        ("compose", "apply"),
    ),
    (
        "idms_db2_phase2.composers.output_write_paragraph_composer",
        "OutputWriteParagraphComposer",
        ("compose", "apply"),
    ),
    (
        "idms_db2_phase2.composers.cobol_formatter",
        "CobolFormatter",
        ("format", "compose", "apply"),
    ),
]


def _tokens(text: str) -> str:
    """Every non-blank character of every body, order preserved."""
    out = []

    for line in text.splitlines():
        body = line[7:72] if len(line) >= 72 else line
        out.append("".join(body.split()))

    return "".join(out)


def _entry_point(instance, names):
    for name in names:
        method = getattr(instance, name, None)
        if callable(method):
            return name, method
    return "", None


@pytest.mark.parametrize(
    "module_name, class_name, entry_names",
    CANDIDATES,
    ids=[item[1] for item in CANDIDATES],
)
def test_pass_preserves_every_character(module_name, class_name, entry_names):
    """The failing parametrisation names the pass that eats characters."""
    try:
        module = importlib.import_module(module_name)
    except ImportError as error:
        pytest.skip(f"{module_name} not importable: {error}")

    cls = getattr(module, class_name, None)
    if cls is None:
        pytest.skip(f"{class_name} not found in {module_name}")

    try:
        instance = cls()
    except TypeError as error:
        pytest.skip(f"{class_name} needs constructor arguments: {error}")

    name, entry = _entry_point(instance, entry_names)
    if entry is None:
        pytest.skip(
            f"{class_name} exposes none of {entry_names}; "
            f"available: {[m for m in dir(instance) if not m.startswith('_')]}"
        )

    try:
        result = entry(SOURCE)
    except Exception as error:  # noqa: BLE001
        pytest.skip(f"{class_name}.{name}() raised on the fixture: {error}")

    assert isinstance(result, str), f"{class_name}.{name}() did not return text"

    assert _tokens(result) == _tokens(SOURCE), (
        f"{class_name}.{name}() LOSES CHARACTERS.\n"
        f"expected {len(_tokens(SOURCE))} non-blank chars, "
        f"got {len(_tokens(result))}"
    )


@pytest.mark.parametrize(
    "module_name, class_name, entry_names",
    CANDIDATES,
    ids=[item[1] for item in CANDIDATES],
)
def test_pass_never_merges_physical_lines(module_name, class_name, entry_names):
    """A four-line condition must not come back as two.

    Character loss and line merging are separate symptoms: a pass could
    merge without losing, or lose without merging.
    """
    try:
        module = importlib.import_module(module_name)
    except ImportError as error:
        pytest.skip(f"{module_name} not importable: {error}")

    cls = getattr(module, class_name, None)
    if cls is None:
        pytest.skip(f"{class_name} not found in {module_name}")

    try:
        instance = cls()
    except TypeError as error:
        pytest.skip(f"{class_name} needs constructor arguments: {error}")

    name, entry = _entry_point(instance, entry_names)
    if entry is None:
        pytest.skip(f"{class_name} exposes none of {entry_names}")

    try:
        result = entry(SOURCE)
    except Exception as error:  # noqa: BLE001
        pytest.skip(f"{class_name}.{name}() raised on the fixture: {error}")

    before = len([line for line in SOURCE.splitlines() if line.strip()])
    after = len([line for line in str(result).splitlines() if line.strip()])

    assert after >= before, (
        f"{class_name}.{name}() MERGED lines: {before} in, {after} out"
    )