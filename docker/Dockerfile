# Garage-flavored Hermes Agent image.
#
# One image, multiple roles: the gateway runs by default; the OBD daemon
# runs as a second compose service (profile "car") from the same image.
# All mutable state stays in the /opt/data volume — the image is stateless.
#
# Build (from this directory):  docker build -f docker/Dockerfile -t garage-hermes .
FROM nousresearch/hermes-agent:latest

# Garage data lives under the Hermes state volume in the container.
# Locally, scripts default to ~/.hermes/garage via the same variable.
ENV GARAGE_DATA_DIR=/opt/data/garage

# Default volume-owner mapping for EVERY entry point (gateway, setup wizard,
# one-off commands). Without a default, a plain `docker run ... setup` writes
# files as uid 10000 while a compose-managed gateway later runs as 1000 ->
# mixed ownership + PermissionErrors everywhere. Override on hosts where
# your user isn't uid 1000.
ENV HERMES_UID=1000 \
    HERMES_GID=1000

# --- Garage code (baked; state comes from volumes) --------------------------
COPY mcp_server /opt/garage/mcp_server
COPY ingest /opt/garage/ingest
COPY scripts /opt/garage/scripts
COPY ledger /opt/garage/ledger
RUN python3 -m venv /opt/garage/.venv && \
    /opt/garage/.venv/bin/pip install --no-cache-dir \
        fastmcp sentence-transformers pypdf pymupdf pillow pytesseract numpy obd ocrmypdf && \
    apt-get -o Acquire::Retries=3 update && \
    apt-get install -y --no-install-recommends sqlite3 tesseract-ocr \
        tesseract-ocr-eng tesseract-ocr-deu ghostscript && \
    rm -rf /var/lib/apt/lists/*

# --- Skills + first-boot seeding --------------------------------------------
# /opt/data is a bind-mounted volume, so baked files at that path would be
# shadowed. seed.sh copies skills/config into the volume on first boot only;
# user edits and Hermes updates survive image rebuilds.
COPY skills /opt/garage/skills
COPY docker/config.seed.yaml /opt/garage/config.seed.yaml
COPY docker/soul.seed.md /opt/garage/soul.seed.md
COPY docker/status_phrases.seed.yaml /opt/garage/status_phrases.seed.yaml
COPY docker/research-sources.seed.md /opt/garage/research-sources.seed.md
COPY docker/seed.sh /opt/garage/seed.sh
COPY docker/setup_heartbeats.sh /opt/garage/setup_heartbeats.sh
# Bake the KITT scanner GIF into the image (ffmpeg is in the base):
RUN mkdir -p /opt/garage/assets && \
    python3 /opt/garage/scripts/make_kitt_gif.py /opt/garage/assets && \
    chmod +x /opt/garage/seed.sh /opt/garage/setup_heartbeats.sh

# Default role: gateway (seed first). Other roles via compose `command:`.
CMD ["/opt/garage/seed.sh"]
