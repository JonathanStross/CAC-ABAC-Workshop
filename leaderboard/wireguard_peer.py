"""
wireguard_peer.py — Automatic WireGuard peer creation for workshop participants
================================================================================
Creates a customer-type WireGuard peer by SSH-ing to the host and running the
existing add-peer.sh script. Returns the .conf file content so it can be
displayed and downloaded directly on the registration success page.

Requirements (set in docker-compose.yml):
  - SSH key mounted at WG_SSH_KEY_PATH (default /secrets/wg_ssh_key)
  - /etc/wireguard/peers mounted read-only at /wg-peers inside the container

Environment variables:
  WG_HOST         — Host to SSH into (default 127.0.0.1 — the Docker host)
  WG_SSH_USER     — SSH user (default root)
  WG_SSH_KEY_PATH — Path to private SSH key inside the container
  WG_PEERS_DIR    — Where peer .conf files live inside the container (read-only mount)
  WG_ADD_PEER_CMD — Full path to add-peer.sh on the HOST (default /etc/wireguard/add-peer.sh)
"""

import os
import re
import shutil
import subprocess
import logging

logger = logging.getLogger(__name__)

WG_HOST         = os.environ.get("WG_HOST",         "127.0.0.1")
WG_SSH_USER     = os.environ.get("WG_SSH_USER",     "root")
WG_SSH_KEY_PATH = os.environ.get("WG_SSH_KEY_PATH", "/secrets/wg_ssh_key")
WG_PEERS_DIR    = os.environ.get("WG_PEERS_DIR",    "/wg-peers")
WG_ADD_PEER_CMD = os.environ.get("WG_ADD_PEER_CMD", "/etc/wireguard/add-peer.sh")

WG_AVAILABLE = os.path.exists(WG_SSH_KEY_PATH) and shutil.which("ssh") is not None

if not os.path.exists(WG_SSH_KEY_PATH):
    logger.warning("WireGuard SSH key not found at %s — WG peer auto-creation disabled", WG_SSH_KEY_PATH)
elif shutil.which("ssh") is None:
    logger.warning("'ssh' binary not found in PATH — WG peer auto-creation disabled")


def _ssh(remote_cmd: str) -> tuple[int, str, str]:
    """Run a command on the host via SSH. Returns (returncode, stdout, stderr)."""
    cmd = [
        "ssh",
        "-i", WG_SSH_KEY_PATH,
        "-o", "StrictHostKeyChecking=no",
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=10",
        f"{WG_SSH_USER}@{WG_HOST}",
        remote_cmd,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return result.returncode, result.stdout, result.stderr


def create_customer_peer(display_name: str) -> tuple[bool, str, str, str]:
    """
    Create a customer WireGuard peer for a workshop participant.

    Parameters
    ----------
    display_name : str
        Human-readable name (used in the conf comment and the filename).

    Returns
    -------
    (success, wg_ip, conf_content, error_msg)
        On success  : (True,  "10.8.0.XX", "<full .conf text>", "")
        On failure  : (False, "",           "",                  "<reason>")
    """
    if not WG_AVAILABLE:
        return False, "", "", "WireGuard SSH key not mounted — peer creation is disabled on this server"

    # Sanitise name for the shell command (strip quotes/special chars)
    safe_name = re.sub(r"[^A-Za-z0-9 _\-]", "", display_name).strip()
    if not safe_name:
        safe_name = "Workshop_Participant"

    remote_cmd = f'{WG_ADD_PEER_CMD} --name "{safe_name}" --type customer'
    rc, stdout, stderr = _ssh(remote_cmd)

    if rc != 0:
        logger.error("add-peer.sh failed (rc=%d): %s", rc, stderr)
        return False, "", "", f"add-peer.sh exited with code {rc}: {stderr.strip()}"

    # Parse the assigned IP from script output: "  Assigned IP: 10.8.0.XX"
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
        # Fallback: derive expected filename from safe_name
        safe_filename = safe_name.replace(" ", "_")
        conf_path = f"/etc/wireguard/peers/{safe_filename}_customer.conf"

    # Read the .conf via the read-only mount inside the container
    local_conf_path = os.path.join(WG_PEERS_DIR, os.path.basename(conf_path))
    if os.path.exists(local_conf_path):
        try:
            with open(local_conf_path) as f:
                conf_content = f.read()
            logger.info("WireGuard peer created: %s @ %s", safe_name, wg_ip)
            return True, wg_ip, conf_content, ""
        except OSError as exc:
            logger.error("Could not read conf file %s: %s", local_conf_path, exc)
            return False, wg_ip, "", f"Peer created but conf file unreadable: {exc}"

    # Last resort: read via SSH cat
    rc2, conf_content, err2 = _ssh(f"cat '{conf_path}'")
    if rc2 == 0 and conf_content:
        logger.info("WireGuard peer created (conf via SSH cat): %s @ %s", safe_name, wg_ip)
        return True, wg_ip, conf_content, ""

    return False, wg_ip, "", f"Peer created but could not retrieve conf file from {conf_path}"
