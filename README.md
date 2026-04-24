# Space Goose

Space Goose is a workspace for running and connecting remote Goose coding environments. The repository contains the root Docker Compose setup plus several related components for Kubernetes management, Discord automation, n8n integration, infrastructure, and supporting docs.

## What’s in this repo

- `compose.yml` — root local runtime for the Goose app on `http://localhost:7681`
- `compose-cloudflare.yml` — optional Cloudflare Tunnel companion for exposing the local app
- `k8s-manager/` — FastAPI + MCP service for managing Kubernetes-isolated AI agent projects
- `discord/` — Discord bot that talks to the K8s Manager API
- `n8n-node/` — custom n8n node for sending instructions to Space Goose projects
- `infra/` — Kubernetes manifests and setup helpers
- `scripts/` — stress-test and automation scripts
- `docs/` — implementation notes, plans, and research writeups

## Root local setup

Run the root Goose container with Docker Compose:

```bash
docker compose up
```

Then open the app at [http://localhost:7681](http://localhost:7681).

## Cloudflare Tunnel

To expose the local Goose instance publicly, start Compose with the tunnel companion file:

```bash
docker compose -f compose.yml -f compose-cloudflare.yml up
```

Check the `cloudflared` logs for the public URL.

## Component docs

- `k8s-manager/README.md`
- `discord/QUICKSTART.md`
- `n8n-node/README.md`

Each component also has its own source tree and configuration files, so use the local docs when working on that part of the system.
