#!/bin/bash

# Usage: ./generate-nginx-conf.sh app_blue
# ACTIVE_POOL must be either app_blue or app_green

ACTIVE_POOL=$1

if [ -z "$ACTIVE_POOL" ]; then
    echo "Error: You must provide the active pool (app_blue or app_green)"
    exit 1
fi

# Determine backup pool automatically
if [ "$ACTIVE_POOL" == "app_blue" ]; then
    BACKUP_POOL="app_green"
elif [ "$ACTIVE_POOL" == "app_green" ]; then
    BACKUP_POOL="app_blue"
else
    echo "Error: ACTIVE_POOL must be either app_blue or app_green"
    exit 1
fi

# Generate nginx.conf
cat > ./nginx/nginx.conf <<EOF
worker_processes 1;

events { worker_connections 1024; }

http {
    upstream backend {
        server $ACTIVE_POOL:80 max_fails=2 fail_timeout=5s;
        server $BACKUP_POOL:80 backup;
    }

    server {
        listen 80;

        location / {
            proxy_pass http://backend;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_pass_header X-App-Pool;
            proxy_pass_header X-Release-Id;

            proxy_next_upstream error timeout http_500 http_502 http_503 http_504;
            proxy_next_upstream_tries 2;
            proxy_connect_timeout 2s;
            proxy_read_timeout 5s;
        }
    }
}
EOF

echo "✅ nginx.conf generated with ACTIVE_POOL=$ACTIVE_POOL and BACKUP_POOL=$BACKUP_POOL"

