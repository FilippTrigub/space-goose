# Start from the official Ollama base image
FROM ollama/ollama:latest

# Set environment variable for Ollama host if needed (often defaults correctly)
ENV OLLAMA_HOST=0.0.0.0

# Pull the desired model during the image build process
# This ensures the model is included in the final image layers
RUN ollama serve & sleep 5 && ollama pull qwen2.5:7b

# The base image's default entrypoint/command is 'ollama serve'.
# When a container starts from this image, it will automatically run 'ollama serve'
# with the pre-pulled model available. 