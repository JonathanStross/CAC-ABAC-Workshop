"""
sap_user.py — SAP workshop user provisioning
=============================================
Called from leaderboard.py on participant registration.
Creates a dialog user on the A4H system via RFC (BAPI_USER_CREATE1).

Requirements:
  - SAP NW RFC SDK unpacked into vendor/nwrfcsdk/ (see README)
  - pyrfc installed (pip install pyrfc)
  - Environment variables set (see .env.example)

If pyrfc is not available the module degrades gracefully:
  SAP_AVAILABLE = False  →  leaderboard works, user creation skipped.
"""

import os
import random
import string
import logging
from datetime import date, timedelta

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Try to import pyrfc — optional dependency
# ---------------------------------------------------------------------------
try:
    import pyrfc
    SAP_AVAILABLE = True
except ImportError:
    SAP_AVAILABLE = False
    logger.warning("pyrfc not available — SAP user auto-creation disabled")

# ---------------------------------------------------------------------------
# Config from environment
# ---------------------------------------------------------------------------
SAP_HOST    = os.environ.get("SAP_HOST",     "10.8.0.1")
SAP_SYSNR   = os.environ.get("SAP_SYSNR",   "00")
SAP_CLIENT  = os.environ.get("SAP_CLIENT",  "001")
SAP_USER    = os.environ.get("SAP_USER",    "DEVELOPER")
SAP_PASSWD  = os.environ.get("SAP_PASSWORD", "")

# Workshop user validity window
USER_VALID_FROM = date.today().strftime("%Y%m%d")
USER_VALID_TO   = (date.today() + timedelta(days=90)).strftime("%Y%m%d")

# Role assigned to every workshop participant (instructor must create this in SAP)
# If the role does not exist the user is still created — role assignment is just skipped
WORKSHOP_ROLE = os.environ.get("SAP_WORKSHOP_ROLE", "Z_DAC_WORKSHOP_PARTICIPANT")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _generate_password(length: int = 12) -> str:
    """
    Generate a password that satisfies standard SAP complexity rules:
      - At least one uppercase letter
      - At least one lowercase letter
      - At least one digit
      - At least one special character
      - Does NOT start with ! or ? (SAP rejects those)
    """
    upper   = random.choice(string.ascii_uppercase)
    lower   = random.choice(string.ascii_lowercase)
    digit   = random.choice(string.digits)
    special = random.choice("#$@+")
    rest    = [random.choice(string.ascii_letters + string.digits) for _ in range(length - 4)]
    chars   = [upper, lower, digit, special] + rest
    random.shuffle(chars)
    # Ensure first char is a letter (SAP quirk)
    if not chars[0].isalpha():
        for i in range(1, len(chars)):
            if chars[i].isalpha():
                chars[0], chars[i] = chars[i], chars[0]
                break
    return "".join(chars)


def _sap_connection():
    return pyrfc.Connection(
        ashost=SAP_HOST,
        sysnr=SAP_SYSNR,
        client=SAP_CLIENT,
        user=SAP_USER,
        passwd=SAP_PASSWD,
    )


def _parse_bapiret(return_table) -> list[str]:
    """Return list of error messages from BAPI RETURN table."""
    return [
        f"[{r['TYPE']}] {r['MESSAGE'].strip()}"
        for r in return_table
        if r["TYPE"] in ("E", "A")
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create_workshop_user(
    sap_username: str,
    first_name: str,
    last_name: str,
    email: str,
) -> tuple[bool, str, str]:
    """
    Create a SAP dialog user for a workshop participant.

    Parameters
    ----------
    sap_username : str
        Desired SAP logon name (max 12 chars, will be uppercased).
        The function prepends no prefix — the leaderboard passes it as-is.
    first_name   : str
    last_name    : str
    email        : str

    Returns
    -------
    (success: bool, temp_password: str, error_msg: str)
        On success  : (True,  "<generated password>", "")
        On failure  : (False, "",                     "<reason>")
    """
    if not SAP_AVAILABLE:
        return False, "", "pyrfc not installed — SAP user creation is disabled on this server"

    if not SAP_PASSWD:
        return False, "", "SAP_PASSWORD environment variable is not set"

    sap_username = sap_username.upper().strip()
    if len(sap_username) > 12:
        return False, "", f"SAP username must be ≤ 12 characters (got {len(sap_username)})"

    temp_password = _generate_password()

    try:
        conn = _sap_connection()

        # ---- Create user ------------------------------------------------
        result = conn.call(
            "BAPI_USER_CREATE1",
            USERNAME=sap_username,
            LOGONDATA={
                "USTYP": "A",          # Dialog user
                "GLTGV": USER_VALID_FROM,
                "GLTGB": USER_VALID_TO,
            },
            PASSWORD={"BAPIPWD": temp_password},
            ADDRESS={
                "FIRSTNAME": first_name[:25],
                "LASTNAME":  last_name[:25],
                "E_MAIL":    email[:241],
            },
        )

        errors = _parse_bapiret(result.get("RETURN", []))
        if errors:
            conn.call("BAPI_TRANSACTION_ROLLBACK")
            conn.close()
            return False, "", " | ".join(errors)

        conn.call("BAPI_TRANSACTION_COMMIT", WAIT="X")

        # ---- Assign workshop role (best-effort) --------------------------
        try:
            conn.call(
                "BAPI_USER_ACTGROUPS_ASSIGN",
                USERNAME=sap_username,
                ACTIVITYGROUPS=[{
                    "AGR_NAME": WORKSHOP_ROLE,
                    "AGR_TEXT": "DAC Workshop Participant",
                    "FROM_DAT": USER_VALID_FROM,
                    "TO_DAT":   USER_VALID_TO,
                }],
            )
            conn.call("BAPI_TRANSACTION_COMMIT", WAIT="X")
            logger.info("Role %s assigned to %s", WORKSHOP_ROLE, sap_username)
        except Exception as role_err:
            logger.warning("Role assignment failed (non-fatal): %s", role_err)

        conn.close()
        logger.info("SAP user %s created successfully", sap_username)
        return True, temp_password, ""

    except pyrfc.RFCError as exc:
        logger.error("RFC error creating user %s: %s", sap_username, exc)
        return False, "", str(exc)
    except Exception as exc:
        logger.error("Unexpected error creating user %s: %s", sap_username, exc)
        return False, "", str(exc)


def user_exists(sap_username: str) -> bool:
    """Return True if the SAP username already exists."""
    if not SAP_AVAILABLE or not SAP_PASSWD:
        return False
    try:
        conn = _sap_connection()
        result = conn.call("SUSR_USER_ADDRESS_READ", BNAME=sap_username.upper())
        conn.close()
        # If no exception, user exists
        return True
    except Exception:
        return False
