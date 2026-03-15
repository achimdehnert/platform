#!/usr/bin/env python3
"""Fix PAPERLESS_PROXY_SSL_HEADER in docker-compose.yml."""

path = "/opt/doc-hub/docker-compose.yml"

with open(path, "r") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if "PAPERLESS_PROXY_SSL_HEADER" in line:
        # Paperless uses json.loads() — needs valid JSON array
        # YAML single quotes avoid escaping double quotes
        new_lines.append(
            "      PAPERLESS_PROXY_SSL_HEADER: "
            "'[\"HTTP_X_FORWARDED_PROTO\",\"https\"]'\n"
        )
    else:
        new_lines.append(line)

with open(path, "w") as f:
    f.writelines(new_lines)

# Verify
for i, line in enumerate(new_lines, 1):
    if "PROXY_SSL" in line:
        print(f"Line {i}: {line.rstrip()}")

print("Done.")
