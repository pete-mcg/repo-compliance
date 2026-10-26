# Install only tooling, without any repository source in the build.
# Paths are configured in agent_framework.py, so runtime needs no downloads.

FROM ghcr.io/oraios/serena:2.1.0@sha256:eb52535ff1c292add25c2b2d37b2db4e2e20c60cda7d8e25f9d11490ce0e1bdf

RUN uv venv /opt/pyrefly
RUN uv pip install \
    --python /opt/pyrefly/bin/python \
    pyrefly==1.1.1

RUN npm install \
    --prefix /opt/typescript \
    --ignore-scripts \
    --no-audit \
    --no-fund \
    typescript@5.9.3 \
    typescript-language-server@5.1.3
