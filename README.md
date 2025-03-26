# Goose House

This project sets up [Goose](https://github.com/block/goose) in a containerized environment with a web terminal interface using [ttyd](https://github.com/tsl0922/ttyd).

## Components

- **Goose**: Main application
- **ttyd**: Web terminal interface
- **Docker CLI**: For running containers for MCP servers

## Getting Started

### Prerequisites
- Docker

### Setup

1. Clone this repository:
   ```
   git clone <repository-url>
   cd <repository-directory>
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