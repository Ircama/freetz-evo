#!/bin/sh
# Harden ocs-onthefly against ambiguous redirects when src_pt_info path contains
# whitespace or shell metacharacters.
set -e

TARGET="$1"
if [ -z "$TARGET" ] || [ ! -f "$TARGET" ]; then
    echo "Usage: $0 /path/to/ocs-onthefly" >&2
    exit 2
fi

# Quote src_pt_info when used as grep input file.
sed -i 's|grep -Ew "/dev/$src_dev" $src_pt_info|grep -Ew "/dev/$src_dev" "$src_pt_info"|g' "$TARGET"
sed -i 's|grep -Ew "/dev/$src_p" $src_pt_info|grep -Ew "/dev/$src_p" "$src_pt_info"|g' "$TARGET"

# Quote redirection targets to avoid "ambiguous redirect".
sed -i 's|exec 5< $src_pt_info|exec 5< "$src_pt_info"|g' "$TARGET"
sed -i 's|done < $src_pt_info|done < "$src_pt_info"|g' "$TARGET"

# Sanity checks: fail if legacy unquoted forms are still present.
if grep -q 'grep -Ew "/dev/$src_dev" $src_pt_info' "$TARGET"; then
    echo "ERROR: unquoted src_pt_info use for src_dev still present in $TARGET" >&2
    exit 3
fi
if grep -q 'grep -Ew "/dev/$src_p" $src_pt_info' "$TARGET"; then
    echo "ERROR: unquoted src_pt_info use for src_p still present in $TARGET" >&2
    exit 4
fi
if grep -q 'exec 5< $src_pt_info' "$TARGET"; then
    echo "ERROR: unquoted exec redirect for src_pt_info still present in $TARGET" >&2
    exit 5
fi
if grep -q 'done < $src_pt_info' "$TARGET"; then
    echo "ERROR: unquoted loop redirect for src_pt_info still present in $TARGET" >&2
    exit 6
fi
