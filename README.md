# Hani (goose in Estonian)

This project sets up [Goose](https://github.com/block/goose) in a containerized environment, powered by the Model runner in Docker Desktop and connecting to the AI Tools Catalog by Docker. 

![Screenshot]([https://private-user-images.githubusercontent.com/426039/427021334-4259005e-2d83-4fc0-ba41-80dd44c327dd.png?jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3NDI5OTMzNjMsIm5iZiI6MTc0Mjk5MzA2MywicGF0aCI6Ii80MjYwMzkvNDI3MDIxMzM0LTQyNTkwMDVlLTJkODMtNGZjMC1iYTQxLTgwZGQ0NGMzMjdkZC5wbmc_WC1BbXotQWxnb3JpdGhtPUFXUzQtSE1BQy1TSEEyNTYmWC1BbXotQ3JlZGVudGlhbD1BS0lBVkNPRFlMU0E1M1BRSzRaQSUyRjIwMjUwMzI2JTJGdXMtZWFzdC0xJTJGczMlMkZhd3M0X3JlcXVlc3QmWC1BbXotRGF0ZT0yMDI1MDMyNlQxMjQ0MjNaJlgtQW16LUV4cGlyZXM9MzAwJlgtQW16LVNpZ25hdHVyZT1mOWIyOTRmZWQzZGVjMDAwNGFiZjljZTI0MTE4MDVjODI4NDBlMzBhMjJiNGE5ZDE4OTQ2OGIyNzBmYzE4MDYwJlgtQW16LVNpZ25lZEhlYWRlcnM9aG9zdCJ9.Kbed8ecb-iiiIOtjiXzqO7VuXmWiXtMu3e9Tk5-1WCM](https://private-user-images.githubusercontent.com/426039/427021334-4259005e-2d83-4fc0-ba41-80dd44c327dd.png?jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3NDI5OTYzOTAsIm5iZiI6MTc0Mjk5NjA5MCwicGF0aCI6Ii80MjYwMzkvNDI3MDIxMzM0LTQyNTkwMDVlLTJkODMtNGZjMC1iYTQxLTgwZGQ0NGMzMjdkZC5wbmc_WC1BbXotQWxnb3JpdGhtPUFXUzQtSE1BQy1TSEEyNTYmWC1BbXotQ3JlZGVudGlhbD1BS0lBVkNPRFlMU0E1M1BRSzRaQSUyRjIwMjUwMzI2JTJGdXMtZWFzdC0xJTJGczMlMkZhd3M0X3JlcXVlc3QmWC1BbXotRGF0ZT0yMDI1MDMyNlQxMzM0NTBaJlgtQW16LUV4cGlyZXM9MzAwJlgtQW16LVNpZ25hdHVyZT0xOGIxN2IxOGJlOWIzY2RlMjI5OWZhYTA3YTgyZDA4ODg4OWY1YmYwYzZhZmVmYTI1YTM3NjVkZGMzNDMxN2E4JlgtQW16LVNpZ25lZEhlYWRlcnM9aG9zdCJ9.yOEOSw70hMXhA2ECm0AZyPaKfB1tl8veBU5FckLG7YQ))

If you have a Docker Desktop with the Model runner installed, you can run it locally: 

```
docker run -it --rm -v /var/run/docker.sock:/var/run/docker.sock -p 7681:7681 olegselajev241/hani
```

Override  the default model selection: 
```
docker run -it --rm -v /var/run/docker.sock:/var/run/docker.sock -p 7681:7681 -e GOOSE_MODEL=ai/mistral-nemo:12B-Q4_K_M olegselajev241/hani
```

Prefer tools-aware models, Goose is an MCP client, so giving it access to tools multiplies the usefullness by a lot. 

## Components

- **Goose**: Main application
- **ttyd**: Web terminal interface
- **Docker CLI**: For running socat container to access AI Tools catalog

## Getting Started

### Prerequisites
- Docker

### Setup

1. Clone this repository:
   ```
   git clone https://github.com/shelajev/hani.git
   cd hani
   ```

2. Build and run the container (sets Docker context to default, because it maps socket into container to run other containers)
   ```
   ./build.sh
   ```
3. Open Goose session in the browser: [http://localhost:7681](http://localhost:7681)

## Customization

To customize the Goose container, modify the `Dockerfile` and rebuild:

```
./build.sh
``` 
