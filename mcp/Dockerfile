# Install only tooling, without any repository source in the build.
# Paths are configured in agent_framework.py, so runtime needs no downloads.

FROM ghcr.io/oraios/serena:1.7.0@sha256:6c9459e4246a39c9deaa4f23fb05a526ac6e237b24c8e84a927a098fa1ab6730

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
