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

# Install ttyd from GitHub releases
RUN wget -O /tmp/ttyd.x86_64 https://github.com/tsl0922/ttyd/releases/download/1.7.7/ttyd.x86_64 && \
    chmod +x /tmp/ttyd.x86_64 && \
    mv /tmp/ttyd.x86_64 /usr/local/bin/ttyd


# Download and install Goose
RUN wget -qO- https://github.com/block/goose/releases/download/stable/download_cli.sh | CONFIGURE=false bash && \
    ls -la /root/.local/bin/goose && \
    /root/.local/bin/goose --version  
    
COPY config.yaml /root/.config/goose/config.yaml 
RUN chmod u-w /root/.config/goose/config.yaml
# copy goosehints too as business logic! 

# Expose port for ttyd
EXPOSE 7681

# # Configure Docker Model Runner as the default AI backend 
ENV OPENAI_API_KEY=irrelevant
ENV GOOSE_MODEL=change_me

# Set entrypoint to ttyd running goose session
ENTRYPOINT ["ttyd", "-W"]
CMD ["goose"]