# Space Goose

Space Goose helps you:

- run an adapted Goose coding environment locally
- manage Kubernetes-isolated AI agent projects
- connect Discord and n8n workflows to Goose projects
- use the supporting infra, scripts, and docs to operate the platform with less friction

## What’s in this repo

- `compose.yml` — root local runtime for the Goose app on `http://localhost:7681`
- `compose-cloudflare.yml` — optional Cloudflare Tunnel companion for exposing the local app
- `k8s-manager/` — FastAPI + MCP service for managing Kubernetes-isolated AI agent projects
- `discord/` — Discord bot that connects chat workflows to the K8s Manager API
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

If you want the short version: Space Goose is trying to feel like a Vercel-style platform for Goose-powered environments — fast to launch, easy to connect, and built around the workflows people actually use.

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
