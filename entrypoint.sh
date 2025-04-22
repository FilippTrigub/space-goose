#!/bin/sh
set -e # Exit immediately if a command exits with a non-zero status.

# Hide processes from users inside ttyd for security (optional but recommended)
# --- Removing hidepid for simplicity --- 
# /usr/local/bin/hidepid_umount.sh > /dev/null 2>&1 || true # Ignore errors if already unmounted
# mount -o remount,rw,hidepid=2 /proc
# /usr/local/bin/hidepid_mount.sh > /dev/null 2>&1 || true # Ignore errors if already mounted

# Start ttyd in the background
# Listen on internal port 7681
# Allow connections only from localhost (via nginx)
# The command to run is 'goose session'
echo "Starting ttyd..."
ttyd --port 7681 --interface lo --writable sh -c 'goose' & 

# Start the Node.js authentication app in the background
echo "Starting Node.js auth app..."
cd /app/app
node server.js &
cd /app

# Start nginx in the foreground
# nginx -g 'daemon off;' will keep the container running
echo "Starting nginx..."
nginx -g 'daemon off;'

echo "Entrypoint finished." 