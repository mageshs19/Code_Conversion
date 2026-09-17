# IDMS DB2 Phase 2 Converter

Standalone Phase 2 project for converting IDMS COBOL programs into DB2 embedded SQL COBOL.

## Inputs

- Sheet Mapping Excel or CSV
- DCLGEN text file or multiple DCLGEN files
- Copybook text file
- Optional Copybook PDF
- IDMS COBOL source code

## Output

- Converted DB2 COBOL code
- Validation messages
- Metadata overview
- Record summary
- Column summary
- Set / relationship summary
- Sheet Mapping preview

## Clean Architecture Rule

Hardcoded names, aliases, regex patterns, and business rules must not live inside parsers or services.

Use:

- `catalogs/` for column names, aliases, SQL type lists, labels, and static catalog values
- `patterns/` for regex patterns
- `rules/` for business and conversion rules
- `src/idms_db2_phase2/parsers/` for parsing logic only
- `src/idms_db2_phase2/services/`, `generators/`, `resolvers/`, `transformers/`, and `validators/` for logic only

## Run

From the project root:

```bash
set PYTHONPATH=src
python -m streamlit run src/idms_db2_phase2/app.py --server.port 8502

$env:PYTHONPATH = "src"
python src\idms_db2_phase2\testing\run_update.py

python src\idms_db2_phase2\testing\run_retrieval.py
python src\idms_db2_phase2\testing\run_update.py


python src\idms_db2_phase2\testing\batch_execution.py --mode retrieval
python src\idms_db2_phase2\testing\batch_execution.py --no-review
python src\idms_db2_phase2\testing\batch_execution.py --quiet


python -m pip install "pytest>=9.1.1"
$env:PYTHONPATH = "src;."
python -m pytest tests -q


check