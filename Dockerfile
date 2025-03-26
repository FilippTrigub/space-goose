FROM registry.access.redhat.com/ubi9/ubi-minimal:9.5

# Install dependencies
RUN microdnf install -y \
    wget \
    ca-certificates \
    bzip2 \
    tar \
    libxcb \
    dbus-libs \
    && microdnf clean all

ENV PATH="/root/.local/bin:${PATH}"
# Create a directory for Goose and set PATH
WORKDIR /app

# Install Docker CLI
COPY --from=docker:dind /usr/local/bin/docker /root/.local/bin/

# Install ttyd from GitHub releases
RUN wget -O /tmp/ttyd.x86_64 https://github.com/tsl0922/ttyd/releases/download/1.7.7/ttyd.x86_64 && \
    chmod +x /tmp/ttyd.x86_64 && \
    mv /tmp/ttyd.x86_64 /usr/local/bin/ttyd


COPY config.yaml /root/.config/goose/config.yaml
# Download and install Goose
RUN wget -qO- https://github.com/block/goose/releases/download/stable/download_cli.sh | CONFIGURE=false CANARY=true bash && \
    ls -la /root/.local/bin/goose && \
    /root/.local/bin/goose --version  
    
# Expose port for ttyd
EXPOSE 7681

# # Configure LLM runner as an OpenAI compatible API
ENV OPENAI_HOST=http://model-runner.docker.internal
ENV OPENAI_API_KEY=irrelevant
ENV OPENAI_BASE_PATH=/engines/llama.cpp/v1/chat/completions 


ENV GOOSE_PROVIDER=openai
ENV GOOSE_MODEL=ai/qwen2.5:7B-Q4_K_M

# Set entrypoint to ttyd running goose session
ENTRYPOINT ["ttyd", "-W"]
CMD ["goose"]