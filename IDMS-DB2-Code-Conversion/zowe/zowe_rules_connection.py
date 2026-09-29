# LOCATION: zowe/zowe_rules_connection.py
# ACTION: CREATE NEW FILE
"""Connection defaults, URL assembly, headers and encoding.

Constants only.
"""

from __future__ import annotations

DEFAULT_PORT = 443
DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_VERIFY_TLS = False

# Assembled from parts on purpose.
# A complete address literal in source gets auto-linkified by editors and
# paste pipelines, which corrupts the file into invalid Python.
URL_SCHEME = "https"
URL_SCHEME_SEPARATOR = "://"
ZOSMF_DATASETS_PATH = "/zosmf/restfiles/ds"

BASE_URL_TEMPLATE = (
    URL_SCHEME
    + URL_SCHEME_SEPARATOR
    + "{host}:{port}"
    + ZOSMF_DATASETS_PATH
)

CSRF_HEADER = {"X-CSRF-ZOSMF-HEADER": "1"}
DATA_TYPE_HEADER = {"X-IBM-Data-Type": "text"}
TEXT_CONTENT_TYPE = "text/plain; charset=UTF-8"

MEMBER_NAME_MAX_LENGTH = 8
TEXT_ENCODING = "utf-8"
# LOCATION: zowe/zowe_rules_connection.py
# ACTION: APPEND at the end of the file

# A library larger than the z/OSMF item limit truncates its member list,
# and a truncated list is indistinguishable from a missing member.
# 0 means no limit.
MAX_ITEMS_HEADER = {"X-IBM-Max-Items": "0"}

HTTP_OK = 200
HTTP_NOT_FOUND = 404