#!/bin/sh
# Replace GNU-style "tee --append" with busybox-compatible "tee -a" in all
# scripts under the given directory (or a single file).
set -e

TARGET="$1"
if [ -z "$TARGET" ] || [ ! -e "$TARGET" ]; then
    echo "Usage: $0 /path/to/drbl-scripts-dir-or-file" >&2
    exit 2
fi

if [ -f "$TARGET" ]; then
    sed -i 's/tee --append/tee -a/g' "$TARGET"
elif [ -d "$TARGET" ]; then
    grep -RIl --null 'tee --append' "$TARGET" | while IFS= read -r -d '' f; do
        sed -i 's/tee --append/tee -a/g' "$f"
    done
fi
