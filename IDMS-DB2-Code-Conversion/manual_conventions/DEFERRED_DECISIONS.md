# LOCATION: manual_conventions/DEFERRED_DECISIONS.md
# ACTION: CREATE / REPLACE — team-review tracking template

# Deferred Conversion Decisions — COBOL Team Review

This document tracks COBOL-shop conventions observed in **hand-written manual
DB2 conversions** that the automated converter does **NOT** apply automatically.

The converter follows one strict principle:

> Convert ONLY IDMS database statements and mapped field references.
> Every other business line stays byte-for-byte identical to the input.

Each item below is a convention the manual programmer applied as a **rewrite
preference**, not an IDMS→DB2 conversion. The team reviews each one and decides
whether to (a) leave it manual, (b) automate it as a new `rules/` entry, or
(c) block it pending inputs.

---

## How to use this document

For each item:
1. Discuss with the COBOL team.
2. Fill in **Decision**, **Rationale**, **Owner**, **Target date**.
3. If **Automate** → create a `rules/` entry + a test, then update Status to DONE.
4. If **Keep manual** → mark Status CLOSED; no code change.
5. If **Blocked** → note the blocker (e.g. missing Sheet Mapping input).

**Decision values:** `AUTOMATE` | `KEEP MANUAL` | `BLOCKED` | `PENDING`
**Status values:** `OPEN` | `IN REVIEW` | `DONE` | `CLOSED`

---

## Decision Log

### D-1  Paragraph numbering
- **Observed:** `VERWERKING` → `1000-VERWERKING`, `600-GET-TIMESTAMP` → `820000-GET-TIMESTAMP`
- **Converter behavior:** keeps original paragraph names
- **Risk:** style only (no behavior change)
- **Decision:** _______________
- **Rationale:** ______________________________________________
- **Owner:** ______________
- **Target date:** ______________
- **Status:** OPEN

---

### D-2  Processing counters
- **Observed:** adds `WS-TELLER`, `WS-NB-INPUT-UPD-I`, `WS-NB-BFAR-UPD-I` + increment logic
- **Converter behavior:** not added
- **Risk:** HIGH — adds NEW business logic (changes program behavior)
- **Decision:** _______________
- **Rationale:** ______________________________________________
- **Owner:** ______________
- **Target date:** ______________
- **Status:** OPEN

---

### D-3  Restart-table SQL (DZ01RSTV)
- **Observed:** builds `700-SELECT/UPDATE/INSERT-DZ01RSTV` + `700-RESTART-CONTROL`
- **Converter behavior:** emits one "manual redesign required" comment, keeps original lines
- **Risk:** BLOCKED — restart table not in Sheet Mapping input
- **Blocker:** Add restart table (e.g. `DZ01RSTB`) to Sheet Mapping. Then it
  becomes a normal auto-conversion (no manual rule needed).
- **Decision:** BLOCKED (pending Sheet Mapping input)
- **Rationale:** Converter must not invent DB2 names (authority rule).
- **Owner:** ______________
- **Target date:** ______________
- **Status:** OPEN

---

### D-4  Commit-flow restructure
- **Observed:** extracts `800-PROCESS-COMMIT` paragraph; restructures commit-every-100 logic
- **Converter behavior:** keeps original inline commit flow
- **Risk:** HIGH — restructures working business flow
- **Decision:** _______________
- **Rationale:** ______________________________________________
- **Owner:** ______________
- **Target date:** ______________
- **Status:** OPEN

---

### D-5  Header / REMARKS rewrite
- **Observed:** new AUTHOR, DATE-WRITTEN, rewritten REMARKS block
- **Converter behavior:** keeps original header unchanged
- **Risk:** BLOCKED by existing rule: "Do not corrupt COBOL headers such as
  DATE-WRITTEN, AUTHOR, or PROGRAM-ID."
- **Decision:** KEEP MANUAL (recommended — headers are human documentation)
- **Rationale:** Automating header rewrites conflicts with the header-preservation rule.
- **Owner:** ______________
- **Target date:** ______________
- **Status:** OPEN

---

### D-6  EOF flag style
- **Observed:** `SW-EOF PIC X` → `88-level VMDZ205I-EOF / VMDZ205I-NOT-EOF`
- **Converter behavior:** keeps original `SW-EOF`
- **Risk:** style only (behavior equivalent if mapped carefully)
- **Decision:** _______________
- **Rationale:** ______________________________________________
- **Owner:** ______________
- **Target date:** ______________
- **Status:** OPEN

---

### D-7  Multiple date-staging groups
- **Observed:** adds `DA-YYMMDD`, `DA-DDMMCCYY` in addition to `DA-CCYYMMDD`
- **Converter behavior:** generates only `DA-CCYYMMDD` + `DA-CCYYMMDD-R` + `DA-DD-MM-CCYY`
- **Risk:** LOW — extra staging fields; only needed if a specific date format is used
- **Decision:** _______________
- **Rationale:** ______________________________________________
- **Owner:** ______________
- **Target date:** ______________
- **Status:** OPEN

---

## Summary Table (fill during review)

| ID  | Convention                | Decision | Owner | Target | Status |
|-----|---------------------------|----------|-------|--------|--------|
| D-1 | Paragraph numbering       |          |       |        | OPEN   |
| D-2 | Processing counters       |          |       |        | OPEN   |
| D-3 | Restart-table SQL         | BLOCKED  |       |        | OPEN   |
| D-4 | Commit-flow restructure   |          |       |        | OPEN   |
| D-5 | Header / REMARKS rewrite  | KEEP MAN.|       |        | OPEN   |
| D-6 | EOF flag style            |          |       |        | OPEN   |
| D-7 | Date-staging groups       |          |       |        | OPEN   |

---

## Promotion checklist (when a decision = AUTOMATE)

When the team approves automating a convention:

- [ ] Add the constant/template to the appropriate `rules/*.py` file
- [ ] Add regex (if needed) to the appropriate `patterns/*.py` file
- [ ] Wire it into the relevant composer/generator (logic only)
- [ ] Add a unit test proving the convention is applied correctly
- [ ] Add a test proving non-target lines stay unchanged
- [ ] Update this document: set Decision=AUTOMATE, Status=DONE
- [ ] Move the documentation note out of `manual_conventions/` if fully promoted

---

## Guiding principle (do not violate)

> The automated converter is a **surgical IDMS→DB2 translator**, not a program
> rewriter. It converts IDMS database access and mapped field references, and
> preserves all other business logic byte-for-byte. Any convention that adds
> new logic, renames working paragraphs, or restructures flow must be an
> explicit, team-approved rule — never an implicit default.