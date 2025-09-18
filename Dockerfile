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
RUN wget -qO- https://github.com/FilippTrigub/goose-bbai/releases/download/stable/download_cli.sh | CONFIGURE=false bash 
RUN ls -la /root/.local/bin/goose && \
    /root/.local/bin/goose --version  
    
COPY config.yaml /root/.config/goose/config.yaml 
RUN chmod u-w /root/.config/goose/config.yaml
# copy goosehints too as business logic! 

# # Configure Docker Model Runner as the default AI backend 
ENV GOOSE_PROVIDER=openai
ENV OPENAI_HOST=https://api.blackbox.ai
ENV OPENAI_BASE_PATH=/v1/chat/completions
ENV GOOSE_MODEL=blackboxai/google/gemini-2.5-pro
ENV GOOSE_LEAD_MODEL=blackboxai/google/gemini-2.5-pro

ENV BLACKBOX_API_KEY=$BLACKBOX_API_KEY
ENV OPENAI_API_KEY=$OPENAI_API_KEY
ENV OPENROUTER_API_KEY=$OPENROUTER_API_KEY

ENV GOOSE_GITHUB_CLIENT_SECRET=$GOOSE_GITHUB_CLIENT_SECRET
ENV GOOSE_GITHUB_CLIENT_ID=$GOOSE_GITHUB_CLIENT_ID
ENV GOOSE_AUTH_REDIRECT_URL=$GOOSE_AUTH_REDIRECT_URL
ENV GOOSE_AUTH_LISTEN_ADDR=$GOOSE_AUTH_LISTEN_ADDR
ENV GOOSE_NO_BROWSER=$GOOSE_NO_BROWSER

# Expose port for ttyd
EXPOSE 7681

# Set entrypoint to ttyd running goose session
ENTRYPOINT ["ttyd", "-W"]
CMD ["goose"]