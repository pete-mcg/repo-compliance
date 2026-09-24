FROM python:3.14.2-slim-bookworm@sha256:e87711ef5c86aaeaa7031718a69db79d334d94c545c709583f651b8185870941

RUN pip install --no-cache-dir "mcp==1.30.0"

COPY src/repo_compliance/infrastructure/agentic/repository_files.py /app/server.py

USER 65532:65532

ENTRYPOINT ["python", "/app/server.py"]
