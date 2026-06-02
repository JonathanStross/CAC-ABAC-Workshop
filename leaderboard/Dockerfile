FROM python:3.11-slim

# ---------------------------------------------------------------------------
# SAP NW RFC SDK (optional)
# Place the unpacked SDK into leaderboard/vendor/nwrfcsdk/ before building.
# Download from: https://support.sap.com  (search "SAP NW RFC SDK")
# Expected layout: vendor/nwrfcsdk/lib/libsapnwrfc.so  (Linux x86_64)
# ---------------------------------------------------------------------------
COPY vendor/nwrfcsdk /nwrfcsdk

ENV NWRFCSDK_PATH=/nwrfcsdk
ENV LD_LIBRARY_PATH=/nwrfcsdk/lib
ENV SAPNWRFC_HOME=/nwrfcsdk

WORKDIR /app

# Install Flask (always required) + openssh-client for WireGuard peer creation
RUN pip install --no-cache-dir flask && \
    apt-get update -qq && \
    apt-get install -y --no-install-recommends openssh-client && \
    rm -rf /var/lib/apt/lists/*

# Install pyrfc from SAP GitHub source if the NW RFC SDK is present.
# All PyPI releases are yanked for Python 3.11 — source build required.
# Needs build tools + Cython for the C extension.
RUN if [ -f /nwrfcsdk/lib/libsapnwrfc.so ]; then \
      apt-get update -qq && \
      apt-get install -y --no-install-recommends gcc g++ git cython3 python3-dev libpython3-dev && \
      pip install --no-cache-dir cython && \
      pip install --no-cache-dir git+https://github.com/SAP/PyRFC.git && \
      apt-get purge -y gcc git python3-dev libpython3-dev && \
      apt-get autoremove -y && rm -rf /var/lib/apt/lists/* ; \
    else \
      echo "NW RFC SDK not found — pyrfc skipped, SAP user auto-creation disabled" ; \
    fi

COPY leaderboard.py .
COPY sap_user.py .
COPY wireguard_peer.py .
COPY pathlock-logo.svg .
COPY level_codes.json /data/level_codes.json

VOLUME ["/data"]
EXPOSE 9000

CMD ["python3", "leaderboard.py"]
