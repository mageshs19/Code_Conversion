# Manual Conventions (Deferred — Pending COBOL Team Review)

This folder documents COBOL-shop conventions observed in **hand-written**
manual DB2 conversions that the automated converter does **NOT** apply.

## Why these are separate

The automated converter follows one strict principle:

> Convert ONLY IDMS database statements and mapped field references.
> Every other business line stays byte-for-byte identical to the input.

The conventions listed here are **human-rewrite preferences**, not IDMS→DB2
conversions. They restructure or re-style working business logic. Applying
them automatically would violate the "preserve business logic" rule and risk
introducing bugs.

## Status: DEFERRED

These are documented here for a **future discussion with the COBOL team**.
Once the team confirms which conventions should be standardized, selected
items may be promoted into active `rules/` (with tests) — one at a time.

## What is NOT here (already automated)

The following ARE done automatically by the converter:
- OBTAIN CALC / STORE / MODIFY / ERASE -> DB2 SQL
- FINISH -> COMMIT
- IDMS control statement removal
- Mapped field reference rewrite (FIELD OF RECORD -> DCLGEN host)
- DA_/DT_ date column conversion
- DCLGEN INCLUDE, timestamp WS, date WS generation
- SQLCODE handling (EVALUATE SQLCODE), QUERYNO

## What IS here (deferred conventions)

See the files in this folder. Each documents one convention category.