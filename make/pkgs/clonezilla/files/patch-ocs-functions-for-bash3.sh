#!/bin/sh
set -e

TARGET="$1"
if [ -z "$TARGET" ] || [ ! -f "$TARGET" ]; then
    echo "Usage: $0 /path/to/ocs-functions" >&2
    exit 2
fi

TMP_FILE="${TARGET}.tmp.$$"

awk '
BEGIN { inblock=0; replaced=0 }
{
  if (!inblock && $0 ~ /^  # For very fast lookups, load the globally defined reserved words$/) {
    inblock=1
    replaced=1
    print "  local formatted_names=\"\""
    print "  for item in \"$@\"; do"
    print "    local is_reserved=\"no\""
    print "    for word in $ocs_reserved_dev_name; do"
    print "      if [ \"$item\" = \"$word\" ]; then"
    print "        is_reserved=\"yes\""
    print "        break"
    print "      fi"
    print "    done"
    print "    if [ \"$is_reserved\" = \"yes\" ]; then"
    print "      formatted_names=\"${formatted_names:+${formatted_names} }$item\""
    print "    else"
    print "      # It\047s a device name."
    print "      # First, normalize it by stripping any existing \"/dev/\" prefix."
    print "      local bare_name=\"${item#\"/dev/\"}\""
    print "      formatted_names=\"${formatted_names:+${formatted_names} }/dev/$bare_name\""
    print "    fi"
    print "  done"
    print ""
    print "  echo \"$formatted_names\""
    next
  }

  if (inblock) {
    if ($0 ~ /^  echo "\$\{formatted_names\[@\]\}"$/) {
      inblock=0
      next
    }
    next
  }

  print
}
END {
  if (!replaced) {
    exit 3
  }
}
' "$TARGET" > "$TMP_FILE"

mv "$TMP_FILE" "$TARGET"

# Replace bash4 lowercase expansion with a bash3-compatible form.
sed -i 's/${ocs_sr_type,,}/$(printf '\''%s'\'' "$ocs_sr_type" | tr '\''[:upper:]'\'' '\''[:lower:]'\'')/g' "$TARGET"

# Ensure MULTIPATH_INFODIR always points to a writable location in /tmp.
awk '
BEGIN { inserted=0 }
{
  print
  if (!inserted && $0 ~ /^#$/ && prev ~ /^###$/) {
    print "# Freetz compatibility: provide a writable default for multipath info files."
    print "if [ -z \"$MULTIPATH_INFODIR\" ]; then"
    print "  MULTIPATH_INFODIR=\"$(mktemp -d /tmp/multipath_info.XXXXXX 2>/dev/null || echo /tmp/multipath_info)\""
    print "fi"
    print "mkdir -p \"$MULTIPATH_INFODIR\" 2>/dev/null || MULTIPATH_INFODIR=\"/tmp\""
    print "export MULTIPATH_INFODIR"
    print ""
    inserted=1
  }
  prev=$0
}
END {
  if (!inserted) exit 7
}
' "$TARGET" > "$TMP_FILE"
mv "$TMP_FILE" "$TARGET"

# Skip empty disk tokens before multipath filename generation.
sed -i '/^[[:space:]]*disk=\$(get_diskname "\$p")$/a\
    [ -z "$disk" ] && continue' "$TARGET"

# Guard against dialog/whiptail stderr parse errors being treated as user selections.
awk '
BEGIN { inserted=0 }
{
  print
  if (!inserted && $0 ~ /^[[:space:]]*target_dev="\$\(cat \$TMP\)"$/) {
    print "      target_dev_clean=\"$(echo \"$target_dev\" | tr -d \"\\\"\")\""
    print "      target_dev_invalid=\"\""
    print "      if [ -n \"$target_dev_clean\" ]; then"
    print "        for idev in $target_dev_clean; do"
    print "          dev_candidate=\"$idev\""
    print "          case \"$dev_candidate\" in"
    print "            ocs-[smn]d*[[]*[]])"
    print "              dev_candidate=\"${dev_candidate#*[}\""
    print "              dev_candidate=\"${dev_candidate%]}\""
    print "              ;;"
    print "          esac"
    print "          if ! echo \" $dev_list \" | grep -Eq \"(^|[[:space:]])${dev_candidate}([[:space:]]|$)\"; then"
    print "            target_dev_invalid=\"yes\""
    print "            break"
    print "          fi"
    print "        done"
    print "      fi"
    print "      if [ \"$target_dev_invalid\" = \"yes\" ]; then"
    print "        echo \"Warning: invalid device selection output from $DIA: $target_dev\" | tee -a ${OCS_LOGFILE}"
    print "        echo \"Falling back to command-line device selection.\" | tee -a ${OCS_LOGFILE}"
    print "        echo \"Available devices: $dev_list\" | tee -a ${OCS_LOGFILE}"
    print "        if [ -r /dev/tty ]; then"
    print "          printf \"Enter target device(s): \" >/dev/tty"
    print "          if ! IFS= read -r target_dev </dev/tty; then"
    print "            echo \"ERROR: unable to read target device from tty.\" | tee -a ${OCS_LOGFILE}"
    print "            exit 1"
    print "          fi"
    print "        else"
    print "          printf \"Enter target device(s): \""
    print "          if ! IFS= read -r target_dev; then"
    print "            echo \"ERROR: unable to read target device from stdin.\" | tee -a ${OCS_LOGFILE}"
    print "            exit 1"
    print "          fi"
    print "        fi"
    print "        target_dev_clean=\"$(echo \"$target_dev\" | tr -d \"\\\"\")\""
    print "        target_dev_invalid=\"\""
    print "        if [ -z \"$target_dev_clean\" ]; then"
    print "          ASK_INPUT=1"
    print "          continue"
    print "        fi"
    print "        for idev in $target_dev_clean; do"
    print "          dev_candidate=\"$idev\""
    print "          case \"$dev_candidate\" in"
    print "            ocs-[smn]d*[[]*[]])"
    print "              dev_candidate=\"${dev_candidate#*[}\""
    print "              dev_candidate=\"${dev_candidate%]}\""
    print "              ;;"
    print "          esac"
    print "          if ! echo \" $dev_list \" | grep -Eq \"(^|[[:space:]])${dev_candidate}([[:space:]]|$)\"; then"
    print "            target_dev_invalid=\"yes\""
    print "            break"
    print "          fi"
    print "        done"
    print "        if [ \"$target_dev_invalid\" = \"yes\" ]; then"
    print "          echo \"Warning: invalid text-mode selection: $target_dev\" | tee -a ${OCS_LOGFILE}"
    print "          ASK_INPUT=1"
    print "          continue"
    print "        fi"
    print "      fi"
    inserted=1
  }
}
END {
  if (!inserted) exit 10
}
' "$TARGET" > "$TMP_FILE"
mv "$TMP_FILE" "$TARGET"

# Exclude read-only block devices and partitions from candidate lists.
awk '
BEGIN { inserted=0 }
{
  if (!inserted && $0 ~ /^  # 2\. FILTER THE MAIN LISTS ONCE$/) {
    print "  echo -n \"Excluding read-only $dev_type...\""
    print "  for dev in $all_disks $all_partitions; do"
    print "    [[ -n \"$dev\" ]] || continue"
    print "    echo -n ."
    print "    ro_val=\"\""
    print "    if [ -r \"/sys/class/block/$dev/ro\" ]; then"
    print "      ro_val=\"$(cat /sys/class/block/$dev/ro 2>/dev/null)\""
    print "    elif command -v blockdev >/dev/null 2>&1; then"
    print "      ro_val=\"$(blockdev --getro /dev/$dev 2>/dev/null)\""
    print "    fi"
    print "    if [ \"$ro_val\" = \"1\" ]; then"
    print "      excluded_devices+=(\"$dev\")"
    print "      excluded_devices+=(\"$(get_diskname \"$dev\")\")"
    print "    fi"
    print "  done"
    print "  echo"
    inserted=1
  }
  print
}
END {
  if (!inserted) exit 8
}
' "$TARGET" > "$TMP_FILE"
mv "$TMP_FILE" "$TARGET"

if grep -q 'local -A reserved_map' "$TARGET"; then
    echo "ERROR: bash4 associative array block still present in $TARGET" >&2
    exit 4
fi
if grep -q '\[\[ -v reserved_map\[' "$TARGET"; then
    echo "ERROR: bash4 [[ -v ]] check still present in $TARGET" >&2
    exit 5
fi
if grep -Ev '^[[:space:]]*#' "$TARGET" | grep -Eq '\$\{[A-Za-z_][A-Za-z0-9_]*,,\}'; then
  echo "ERROR: bash4 lowercase expansion still present in $TARGET" >&2
  exit 6
fi
if ! grep -q 'Warning: invalid device selection output from' "$TARGET"; then
  echo "ERROR: dialog output validation patch not present in $TARGET" >&2
  exit 9
fi
