FROM registry.access.redhat.com/ubi9/ubi-minimal:9.6
# Install dependencies
RUN microdnf install -y \
    wget \
    ca-certificates \
    bzip2 \
    tar \
    libxcb \
    dbus-libs \
    nodejs \
    npm \
    && microdnf clean all


RUN microdnf update -y --nodocs
RUN microdnf module reset nodejs
RUN microdnf module -y enable nodejs:22
RUN microdnf -y install tar gzip nodejs-1:22.19.0-2.module+el9.6.0+23473+45664c2d.x86_64 npm --nodocs
RUN microdnf clean all


ENV PATH="/root/.local/bin:${PATH}"
# Create a directory for Goose and set PATH
WORKDIR /app

# Install ttyd from GitHub releases
RUN wget -O /tmp/ttyd.x86_64 https://github.com/tsl0922/ttyd/releases/download/1.7.7/ttyd.x86_64 && \
    chmod +x /tmp/ttyd.x86_64 && \
    mv /tmp/ttyd.x86_64 /usr/local/bin/ttyd


# Download and install Goose
RUN wget -qO- https://github.com/FilippTrigub/goose-bbai/releases/download/stable/download_cli.sh | CONFIGURE=false bash 
RUN ls -la /root/.local/bin/goose && \
    /root/.local/bin/goose --version  
    
RUN mkdir -p /root/.config/goose

# Copy pre-configured config.yaml
COPY .config/goose/config.yaml /root/.config/goose/config.yaml

RUN chmod u-w /root/.config/goose/config.yaml
# copy goosehints too as business logic! 

# # Configure Docker Model Runner as the default AI backend 
ENV GOOSE_PROVIDER=openai
ENV OPENAI_HOST=https://api.blackbox.ai
ENV OPENAI_BASE_PATH=/v1/chat/completions
ENV GOOSE_MODEL=blackboxai/google/gemini-2.5-pro
ENV GOOSE_LEAD_MODEL=blackboxai/google/gemini-2.5-pro

# Expose port for ttyd
EXPOSE 7681

# Set entrypoint to ttyd running goose session
ENTRYPOINT ["ttyd", "-W"]
CMD ["goose"]
