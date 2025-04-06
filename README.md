# Hani (goose in Estonian)

This project sets up [Goose](https://github.com/block/goose) in a containerized environment, powered by the Model runner in Docker Desktop and connecting to the AI Tools Catalog by Docker. 

![Screenshot](https://private-user-images.githubusercontent.com/426039/427021334-4259005e-2d83-4fc0-ba41-80dd44c327dd.png?jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3NDI5OTY0NjQsIm5iZiI6MTc0Mjk5NjE2NCwicGF0aCI6Ii80MjYwMzkvNDI3MDIxMzM0LTQyNTkwMDVlLTJkODMtNGZjMC1iYTQxLTgwZGQ0NGMzMjdkZC5wbmc_WC1BbXotQWxnb3JpdGhtPUFXUzQtSE1BQy1TSEEyNTYmWC1BbXotQ3JlZGVudGlhbD1BS0lBVkNPRFlMU0E1M1BRSzRaQSUyRjIwMjUwMzI2JTJGdXMtZWFzdC0xJTJGczMlMkZhd3M0X3JlcXVlc3QmWC1BbXotRGF0ZT0yMDI1MDMyNlQxMzM2MDRaJlgtQW16LUV4cGlyZXM9MzAwJlgtQW16LVNpZ25hdHVyZT04ZDkxZDQwN2Y1ODcyZGMxNjZlM2Q3MTQ3ZDVmY2UyZGU3ZTUwMjQzOWQ0ZDQwOWJiOThiYWRhMWU4YzA4OTYyJlgtQW16LVNpZ25lZEhlYWRlcnM9aG9zdCJ9.P3w-vj5ibD0IHJp64CuZqMSl2npGvggG0gIoq0h-bXY)

If you have a Docker Desktop with the Model runner installed, you can run it locally: 

```
docker run -it --rm -v /var/run/docker.sock:/var/run/docker.sock -p 7681:7681 olegselajev241/hani:local
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
