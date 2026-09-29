# LOCATION: tools/child_check.py
# ACTION: CREATE NEW FILE
"""What input root will the conversion child actually use?"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for candidate in (ROOT, ROOT / "src"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

CODE = (
    "import os;"
    "import config.path_settings as p;"
    "print('  IDMS_INPUT_DIR =', os.environ.get('IDMS_INPUT_DIR', '<< NOT SET >>'));"
    "print('  program folder =', p.DEFAULT_RETRIEVAL_PROGRAM_DIR);"
    "print('  mapping folder =', p.DEFAULT_MAPPING_SHEET_DIR)"
)

from zowe.zowe_steps import subprocess_environment  # noqa: E402

print("")
print("CHILD PROCESS VIEW")
print("-" * 74)
subprocess.run([sys.executable, "-c", CODE], env=subprocess_environment(), check=False)