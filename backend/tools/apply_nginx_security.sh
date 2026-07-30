#!/usr/bin/env bash
set -euo pipefail

source_file="${1:-/opt/factory_shift/deployment/nginx/factory_shift_security.conf}"
target_file="/etc/nginx/snippets/factory_shift_security.conf"
nginx_config="/etc/nginx/nginx.conf"
include_line="    include /etc/nginx/snippets/factory_shift_security.conf;"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "This script must run as root." >&2
  exit 1
fi

if [[ ! -f "$source_file" ]]; then
  echo "Security snippet not found: $source_file" >&2
  exit 1
fi

install -D -m 0644 "$source_file" "$target_file"

if ! grep -Fq "$include_line" "$nginx_config"; then
  backup_file="${nginx_config}.factory-shift.$(date -u +%Y%m%d%H%M%S).bak"
  cp "$nginx_config" "$backup_file"
  python3 - "$nginx_config" "$include_line" <<'PY'
from pathlib import Path
import sys

config_path = Path(sys.argv[1])
include_line = sys.argv[2]
content = config_path.read_text()
marker = "http {\n"
if marker not in content:
    raise SystemExit("nginx http block not found")
config_path.write_text(content.replace(marker, f"{marker}{include_line}\n", 1))
PY
fi

nginx -t
systemctl reload nginx
echo "nginx_security_headers_enabled=true"
