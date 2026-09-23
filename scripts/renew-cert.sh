#!/usr/bin/env bash
set -euo pipefail

cd /root/Listik-bot

docker compose -f docker-compose.yml -f docker-compose.postgres.yml --profile certbot run --rm --no-deps certbot renew \
    --webroot \
    --webroot-path /var/www/certbot \
    --preferred-profile shortlived \
    --non-interactive \
    --quiet

docker exec grocery-caddy caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile
