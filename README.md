# Space Goose

Forked from [Hani](https://github.com/BlockDev/hani).
Deploys goose to the cloud.

## Usage

This project is intended to be run with `docker compose`.

1.  Run the project using `docker compose`:
    ```bash
    docker compose up
    ```
3.  Access the Goose session in your browser at [http://localhost:7681](http://localhost:7681).

## Cloudflare Tunnel

This project includes a service for creating a Cloudflare Tunnel, which can be used to expose your local Goose instance to the internet. To use it, you need to have `cloudflared` configured.

You can start the tunnel by including the `compose-cloudflare.yml` file in your `docker compose` command:

```bash
docker compose -f compose.yml -f compose-cloudflare.yml up
```

Figure out from the logs the public url that points to your Goose container. 