FROM registry.access.redhat.com/ubi9/ubi-minimal:9.5

    # Install dependencies
    RUN microdnf install -y \
        wget \
        ca-certificates \
        bzip2 \
        tar \
        libxcb \
        dbus-libs \
        nginx \
        nodejs \
        && microdnf clean all && \
        # Install necessary npm packages globally if needed or handle in app directory
        npm install -g node-process-hider && \
        # Create default nginx directories if they don't exist
        mkdir -p /var/log/nginx /var/cache/nginx /run/nginx && \
        # Ensure nginx user exists and set permissions (adjust user/group as needed)
        useradd nginx || true && \
        chown -R nginx:nginx /var/log/nginx /var/cache/nginx /run/nginx /var/lib/nginx && \
        chmod -R 755 /var/log/nginx /var/cache/nginx /run/nginx /var/lib/nginx

ENV PATH="/root/.local/bin:${PATH}"
# Create a directory for Goose and set PATH
WORKDIR /app

# Install Docker CLI
COPY --from=docker:dind /usr/local/bin/docker /root/.local/bin/

# Install ttyd from GitHub releases
RUN wget -O /tmp/ttyd.x86_64 https://github.com/tsl0922/ttyd/releases/download/1.7.7/ttyd.x86_64 && \
    chmod +x /tmp/ttyd.x86_64 && \
    mv /tmp/ttyd.x86_64 /usr/local/bin/ttyd

ARG SETUP=local

COPY config-${SETUP}.yaml /root/.config/goose/config.yaml
# Download and install Goose
RUN wget -qO- https://github.com/block/goose/releases/download/stable/download_cli.sh | CONFIGURE=false bash && \
    ls -la /root/.local/bin/goose && \
    /root/.local/bin/goose --version

# Copy Node.js app
COPY app/ /app/app/
WORKDIR /app/app
RUN npm install
WORKDIR /app

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Copy entrypoint script
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Expose port for nginx
EXPOSE 8080

# Configure Docker Model Runner as the default target
ENV OPENAI_API_KEY=irrelevant
ENV GOOGLE_API_KEY=irrelevant
ENV GOOSE_PROVIDER=openai
ENV GOOSE_MODEL=ai/qwen2.5:7B-Q4_K_M

# Run entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"]
CMD []