# Hani (goose in Estonian)

This project sets up [Goose](https://github.com/block/goose) in a containerized environment, powered by the Model runner in Docker Desktop and connecting to the AI Tools Catalog by Docker. 

![Screenshot](https://private-user-images.githubusercontent.com/426039/427021334-4259005e-2d83-4fc0-ba41-80dd44c327dd.png?jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3NDM5NDMyNzYsIm5iZiI6MTc0Mzk0Mjk3NiwicGF0aCI6Ii80MjYwMzkvNDI3MDIxMzM0LTQyNTkwMDVlLTJkODMtNGZjMC1iYTQxLTgwZGQ0NGMzMjdkZC5wbmc_WC1BbXotQWxnb3JpdGhtPUFXUzQtSE1BQy1TSEEyNTYmWC1BbXotQ3JlZGVudGlhbD1BS0lBVkNPRFlMU0E1M1BRSzRaQSUyRjIwMjUwNDA2JTJGdXMtZWFzdC0xJTJGczMlMkZhd3M0X3JlcXVlc3QmWC1BbXotRGF0ZT0yMDI1MDQwNlQxMjM2MTZaJlgtQW16LUV4cGlyZXM9MzAwJlgtQW16LVNpZ25hdHVyZT1hYTQ5ZWViOWVmMzZjZDg5OGZkYmM5MGI4NDg4YmQ1MjllOWM3ZTEzOWMwMGYwZjc4MGI4ODQzZGY1ZmYyNjZiJlgtQW16LVNpZ25lZEhlYWRlcnM9aG9zdCJ9.pnRW0KUG12xxgX3JCQxgVYXUMTlyEwpTiWc29vCeB2E)

If you have a Docker Desktop with the Model runner installed, you can run it locally: 

```
docker run -it --rm -v /var/run/docker.sock:/var/run/docker.sock -p 7681:7681 olegselajev241/hani:local
```

Override  the default model selection: 
```
docker run -it --rm -v /var/run/docker.sock:/var/run/docker.sock -p 7681:7681 -e GOOSE_MODEL=ai/mistral-nemo:12B-Q4_K_M olegselajev241/hani
```

Prefer tools-aware models, Goose is an MCP client, so giving it access to tools multiplies the usefullness by a lot. 


# Compose based setup

If you have a Docker environment with GPU, you can run the compose based setup. 
It uses a Google Maps MCP server, so get your GOOGLE_MAPS_API_KEY, and put it into the `.env` file: 

```
echo GOOGLE_MAPS_API_KEY="changeme" > .env
```

Then spin up the compose: 
```
docker compose up
```

# Cloud run based setup

You can also deploy it to Google Cloud Run. The project setup is a bit involved, you need a GPU quota, a VPC and the secret with the Maps API KEY, but you can check an example of the deployment descriptor in `service.yaml`. 


## Components of the Hani Docker Image

- **Goose**: Main application
- **ttyd**: Web terminal interface
- **Docker CLI**: For running socat container to access AI Tools catalog

### Setup

1. Clone this repository:
   ```
   git clone https://github.com/shelajev/hani.git
   cd hani
   ```

2. Build all the container flavors: 
   ```
   ./build.sh
   ```

3  Run the container locally: 
   ```
   docker run -it --rm -v /var/run/docker.sock:/var/run/docker.sock -p 7681:7681 olegselajev241/hani:local
   ```

4. Open Goose session in the browser: [http://localhost:7681](http://localhost:7681)

