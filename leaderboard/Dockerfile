FROM python:3.11-slim

# ---------------------------------------------------------------------------
# SAP NW RFC SDK (optional)
# Place the unpacked SDK into leaderboard/vendor/nwrfcsdk/ before building
# to enable automatic SAP user creation on registration.
# Without it the leaderboard starts normally — SAP provisioning is disabled.
# Download from: https://support.sap.com  (search "SAP NW RFC SDK")
# Expected layout: vendor/nwrfcsdk/lib/libsapnwrfc.so  (Linux x86_64)
# ---------------------------------------------------------------------------
COPY vendor/nwrfcsdk /nwrfcsdk

ENV NWRFCSDK_PATH=/nwrfcsdk
ENV LD_LIBRARY_PATH=/nwrfcsdk/lib
ENV SAPNWRFC_HOME=/nwrfcsdk

WORKDIR /app

# Install Flask first (always required)
RUN pip install --no-cache-dir flask

# Install pyrfc only if the NW RFC SDK is present (it's a C extension)
RUN if [ -f /nwrfcsdk/lib/libsapnwrfc.so ]; then \
      pip install --no-cache-dir pyrfc; \
    else \
      echo "NW RFC SDK not found — pyrfc skipped, SAP user auto-creation disabled"; \
    fi

COPY leaderboard.py .
COPY sap_user.py .
COPY level_codes.json /data/level_codes.json

VOLUME ["/data"]
EXPOSE 9000

CMD ["python3", "leaderboard.py"]
