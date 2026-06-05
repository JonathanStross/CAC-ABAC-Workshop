"""
wireguard_peer.py — Automatic WireGuard peer creation for workshop participants
================================================================================
Multi-server edition: creates WireGuard peers by SSH-ing to the correct
SAP server (sap2–sap5) based on the slot assigned to the participant.

The peer .conf is retrieved via SSH cat — no read-only mount required.

Environment variables per server (defaults shown):
  WG_SSH_USER           — SSH user for all servers (default root)
  WG_ADD_PEER_CMD       — Path to add-peer.sh on every server
  WG_REMOVE_PEER_CMD    — Path to remove-peer.sh on every server
  SAP2_HOST .. SAP5_HOST — Public IP of each server
  SAP2_WG_KEY .. SAP5_WG_KEY — Container paths to SSH keys for each server

Legacy single-server env vars (kept for backward compat / offgrid):
  WG_HOST, WG_SSH_KEY_PATH, WG_PEERS_DIR
"""

import os
import re
import shutil
import subprocess
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared defaults
# ---------------------------------------------------------------------------
_SSH_USER        = os.environ.get("WG_SSH_USER",      "root")
_ADD_PEER_CMD    = os.environ.get("WG_ADD_PEER_CMD",  "/etc/wireguard/add-peer.sh")
_REMOVE_PEER_CMD = os.environ.get("WG_REMOVE_PEER_CMD", "/etc/wireguard/remove-peer.sh")

# ---------------------------------------------------------------------------
# Multi-server registry — one entry per SAP workshop server
# ---------------------------------------------------------------------------
SERVERS: dict[str, dict] = {
    "sap2": {
        "ssh_host": os.environ.get("SAP2_HOST", "159.195.81.132"),
        "ssh_user": _SSH_USER,
        "ssh_key":  os.environ.get("SAP2_WG_KEY", "/secrets/wg_sap2_key"),
    },
    "sap3": {
        "ssh_host": os.environ.get("SAP3_HOST", "159.195.82.197"),
        "ssh_user": _SSH_USER,
        "ssh_key":  os.environ.get("SAP3_WG_KEY", "/secrets/wg_sap3_key"),
    },
    "sap4": {
        "ssh_host": os.environ.get("SAP4_HOST", "159.195.80.156"),
        "ssh_user": _SSH_USER,
        "ssh_key":  os.environ.get("SAP4_WG_KEY", "/secrets/wg_sap4_key"),
    },
    "sap5": {
        "ssh_host": os.environ.get("SAP5_HOST", "159.195.80.181"),
        "ssh_user": _SSH_USER,
        "ssh_key":  os.environ.get("SAP5_WG_KEY", "/secrets/wg_sap5_key"),
    },
}

# ---------------------------------------------------------------------------
# Legacy single-server config (kept for backward compat / offgrid)
# ---------------------------------------------------------------------------
WG_HOST         = os.environ.get("WG_HOST",         "127.0.0.1")
WG_SSH_KEY_PATH = os.environ.get("WG_SSH_KEY_PATH", "/secrets/wg_ssh_key")
WG_PEERS_DIR    = os.environ.get("WG_PEERS_DIR",    "/wg-peers")
# Also expose for tests / leaderboard.py import
WG_ADD_PEER_CMD    = _ADD_PEER_CMD
WG_REMOVE_PEER_CMD = _REMOVE_PEER_CMD


def _check_wg_available() -> bool:
    if shutil.which("ssh") is None:
        logger.warning("'ssh' binary not found in PATH — WG peer auto-creation disabled")
        return False
    # Any server key present?
    for alias, srv in SERVERS.items():
        if os.path.exists(srv["ssh_key"]):
            return True
    # Legacy key?
    if os.path.exists(WG_SSH_KEY_PATH):
        return True
    logger.warning("No WireGuard SSH keys found — WG peer auto-creation disabled")
    return False


WG_AVAILABLE = _check_wg_available()


# ---------------------------------------------------------------------------
# Low-level SSH helper
# ---------------------------------------------------------------------------

def _ssh_to(srv: dict, remote_cmd: str) -> tuple[int, str, str]:
    """Run *remote_cmd* on *srv* via SSH. Returns (returncode, stdout, stderr)."""
    cmd = [
        "ssh",
        "-i", srv["ssh_key"],
        "-o", "StrictHostKeyChecking=no",
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=10",
        f"{srv['ssh_user']}@{srv['ssh_host']}",
        remote_cmd,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return result.returncode, result.stdout, result.stderr


def _resolve_server(server_alias: str | None) -> dict | None:
    """
    Return the server dict for *server_alias*, or the legacy single-server
    dict if *server_alias* is None/missing. Returns None if unavailable.
    """
    if server_alias and server_alias in SERVERS:
        srv = SERVERS[server_alias]
        if not os.path.exists(srv["ssh_key"]):
            logger.warning("SSH key missing for %s: %s", server_alias, srv["ssh_key"])
            return None
        return srv
    # Legacy / offgrid path
    if os.path.exists(WG_SSH_KEY_PATH):
        return {
            "ssh_host": WG_HOST,
            "ssh_user": _SSH_USER,
            "ssh_key":  WG_SSH_KEY_PATH,
        }
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create_customer_peer(
    display_name: str,
    server_alias: str | None = None,
) -> tuple[bool, str, str, str]:
    """
    Create a customer WireGuard peer on the specified server.

    Parameters
    ----------
    display_name  : Human-readable name (used in the .conf comment/filename).
    server_alias  : One of 'sap2'–'sap5', or None for legacy single-server.

    Returns
    -------
    (success, wg_ip, conf_content, error_msg)
        On success  : (True,  "10.8.0.XX", "<full .conf text>", "")
        On failure  : (False, "",           "",                  "<reason>")
    """
    if not WG_AVAILABLE:
        return False, "", "", "No WireGuard SSH key available — peer creation is disabled"

    srv = _resolve_server(server_alias)
    if srv is None:
        return False, "", "", f"SSH key not available for server '{server_alias}'"

    safe_name = re.sub(r"[^A-Za-z0-9 _\-]", "", display_name).strip() or "Workshop_Participant"
    rc, stdout, stderr = _ssh_to(srv, f'{_ADD_PEER_CMD} --name "{safe_name}" --type customer')

    if rc != 0:
        logger.error("add-peer.sh failed on %s (rc=%d): %s", server_alias or "legacy", rc, stderr)
        return False, "", "", f"add-peer.sh exited {rc}: {stderr.strip()}"

    # Parse assigned IP and conf path from script stdout
    wg_ip = ""
    conf_path = ""
    for line in stdout.splitlines():
        if "Assigned IP:" in line:
            m = re.search(r"(10\.\d+\.\d+\.\d+)", line)
            if m:
                wg_ip = m.group(1)
        if "Config saved to:" in line:
            m = re.search(r"(/etc/wireguard/peers/\S+\.conf)", line)
            if m:
                conf_path = m.group(1)

    if not conf_path:
        safe_filename = safe_name.replace(" ", "_")
        conf_path = f"/etc/wireguard/peers/{safe_filename}_customer.conf"

    # Read .conf via SSH cat (works for any remote server — no mount needed)
    rc2, conf_content, _err2 = _ssh_to(srv, f"cat '{conf_path}'")
    if rc2 == 0 and conf_content:
        logger.info("WireGuard peer created: %s @ %s (server: %s)", safe_name, wg_ip, server_alias or "legacy")
        return True, wg_ip, conf_content, ""

    # Last resort: try the legacy read-only mount (offgrid only)
    if not server_alias:
        local_conf_path = os.path.join(WG_PEERS_DIR, os.path.basename(conf_path))
        if os.path.exists(local_conf_path):
            try:
                with open(local_conf_path) as f:
                    return True, wg_ip, f.read(), ""
            except OSError as exc:
                return False, wg_ip, "", f"Peer created but conf file unreadable: {exc}"

    return False, wg_ip, "", f"Peer created but could not retrieve conf from {conf_path}"


def remove_customer_peer(
    wg_ip: str,
    server_alias: str | None = None,
) -> tuple[bool, str]:
    """
    Remove a WireGuard peer by IP from the specified server.

    Parameters
    ----------
    wg_ip         : The peer's assigned IP (e.g. "10.8.0.5").
    server_alias  : One of 'sap2'–'sap5', or None for legacy single-server.

    Returns (success, error_msg).
    """
    if not WG_AVAILABLE:
        return False, "WireGuard SSH not available"

    srv = _resolve_server(server_alias)
    if srv is None:
        return False, f"SSH key not available for server '{server_alias}'"

    rc, _stdout, stderr = _ssh_to(srv, f"{_REMOVE_PEER_CMD} --ip {wg_ip} --yes")
    if rc != 0:
        logger.error("remove-peer.sh failed for %s on %s (rc=%d): %s",
                     wg_ip, server_alias or "legacy", rc, stderr)
        return False, f"remove-peer.sh exited {rc}: {stderr.strip()}"

    logger.info("WireGuard peer removed: %s (server: %s)", wg_ip, server_alias or "legacy")
    return True, ""
