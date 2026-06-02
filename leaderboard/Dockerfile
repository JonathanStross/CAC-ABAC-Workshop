FROM python:3.11-slim

# ---------------------------------------------------------------------------
# SAP NW RFC SDK
# Place the unpacked SDK into leaderboard/vendor/nwrfcsdk/ before building.
# Download from: https://support.sap.com  (search "SAP NW RFC SDK")
# Expected layout: vendor/nwrfcsdk/lib/libsapnwrfc.so  (Linux x86_64)
# ---------------------------------------------------------------------------
COPY vendor/nwrfcsdk /nwrfcsdk

ENV NWRFCSDK_PATH=/nwrfcsdk
ENV LD_LIBRARY_PATH=/nwrfcsdk/lib
ENV SAPNWRFC_HOME=/nwrfcsdk

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY leaderboard.py .
COPY sap_user.py .
COPY level_codes.json /data/level_codes.json

VOLUME ["/data"]
EXPOSE 9000

CMD ["python3", "leaderboard.py"]
