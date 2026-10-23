# Deployment Guide

NiceTool can run locally with uv or in Docker. Production deployments should use MySQL and a stable storage secret.

## Local

```bash
uv sync --locked
uv run main.py
```

## Docker

Build the environment image:

```bash
docker build --platform linux/amd64 -t nicetool-env -f Dockerfile.env .
```

Run the service:

```bash
docker run -d -p 8000:8000 -v $(pwd):/app --env-file .env --name nicetool nicetool-env
```

When tools need to access services running on the host, add `host.docker.internal`:

```bash
docker run -d -p 8000:8000 -v $(pwd):/app --env-file .env --add-host=host.docker.internal:host-gateway --name nicetool nicetool-env
```

## Production checklist

- Create the MySQL database before startup.
- Set a strong `STORAGE_SECRET`.
- Configure authentication if the instance is shared.
- Back up MySQL and tool source files.
- Keep `.env` out of public commits.
