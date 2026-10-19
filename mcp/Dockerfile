# Install only tooling, without any repository source in the build.
# Paths are configured in agent_framework.py, so runtime needs no downloads.

FROM ghcr.io/oraios/serena:2.0.0@sha256:65406dec0f96f25f883ea487a84762008e0797cd1fcc0aab9cb813c53b2fa215

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
