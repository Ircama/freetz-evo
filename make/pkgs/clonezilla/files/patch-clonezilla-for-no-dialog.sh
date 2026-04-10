#!/bin/sh
set -e

TARGET="$1"
if [ -z "$TARGET" ] || [ ! -f "$TARGET" ]; then
    echo "Usage: $0 /path/to/clonezilla" >&2
    exit 2
fi

TMP_FILE="${TARGET}.tmp.$$"

awk -f - "$TARGET" > "$TMP_FILE" <<'AWK'
BEGIN {
  in_menu_block=0
  replaced_menu=0
  pending_check=0
  replaced_check=0
}
{
  if (pending_check == 1) {
    if ($0 ~ /^check_DIA_set_ESC \$DIA$/) {
      print "if type \"$DIA\" >/dev/null 2>&1; then"
      print "  check_DIA_set_ESC $DIA"
      print "else"
      print "  DIA_ESC=\"\""
      print "  ocs_prompt_mode=\"cmd\""
      print "  ocsroot_src=\"${ocsroot_src:-skip}\""
      print "  chk_ocsroot_mountpont=\"no\""
      print "  export ocs_prompt_mode"
      print "  export ocsroot_src chk_ocsroot_mountpont"
      print "  echo \"Warning: $DIA not found, forcing command-line prompt mode.\""
      print "fi"
      replaced_check=1
      pending_check=0
      next
    }
    pending_check=0
  }

  if (in_menu_block == 1) {
    if ($0 ~ /^    \[ -f "\$TMP" \] && rm -f \$TMP$/) {
      in_menu_block=0
      next
    }
    next
  }

  if ($0 ~ /^  if \[ -z "\$ocs_live_type" \]; then$/) {
    print "  if [ -z \"$ocs_live_type\" ]; then"
    print "    if type \"$DIA\" >/dev/null 2>&1; then"
    print "      $DIA --backtitle \"$msg_nchc_free_software_labs\" --title \"$msg_nchc_clonezilla\" --menu \"$msg_clonezilla_is_free_and_no_warranty \\n$msg_hint_multiple_choice_select_by_space \\n$msg_device_image_device_clone. \\n$msg_lite_server_and_client_are_provided \\n$msg_choose_mode:\" 0 0 0 $DIA_ESC \"device-image\" \"$msg_device_image_clone\" \"device-device\" \"$msg_device_device_clone\" \"remote-source\" \"$msg_remote_clone_source\" \"remote-dest\" \"$msg_remote_clone_destination\" $lite_server_msg_1 $lite_server_msg_2 $lite_client_msg_1 $lite_client_msg_2 2> $TMP"
    print "      ocs_live_type=\"$(cat $TMP)\""
    print "    else"
    print "      echo \"Warning: $DIA not found, using text mode menu.\""
    print "      echo \"1) device-image\""
    print "      echo \"2) device-device\""
    print "      echo \"3) remote-source\""
    print "      echo \"4) remote-dest\""
    print "      if [ \"$show_lite_menu\" = \"yes\" ]; then"
    print "        echo \"5) lite-server\""
    print "        echo \"6) lite-client\""
    print "      fi"
    print "      echo -n \"Choose mode [1]: \""
    print "      read menu_choice"
    print "      case \"$menu_choice\" in"
    print "        \"\"|1) ocs_live_type=\"device-image\" ;;"
    print "        2) ocs_live_type=\"device-device\" ;;"
    print "        3) ocs_live_type=\"remote-source\" ;;"
    print "        4) ocs_live_type=\"remote-dest\" ;;"
    print "        5) ocs_live_type=\"lite-server\" ;;"
    print "        6) ocs_live_type=\"lite-client\" ;;"
    print "        *) ocs_live_type=\"\" ;;"
    print "      esac"
    print "    fi"
    print "    [ -f \"$TMP\" ] && rm -f $TMP"
    in_menu_block=1
    replaced_menu=1
    next
  }

  if ($0 ~ /^# check DIA$/) {
    print $0
    pending_check=1
    next
  }

  print $0
}
END {
  if (!replaced_menu) {
    exit 3
  }
  if (!replaced_check) {
    exit 4
  }
}
AWK

mv "$TMP_FILE" "$TARGET"

if ! grep -q 'using text mode menu' "$TARGET"; then
    echo "ERROR: clonezilla text-mode menu fallback not applied" >&2
    exit 5
fi
if ! grep -q 'forcing command-line prompt mode' "$TARGET"; then
    echo "ERROR: clonezilla DIA check fallback not applied" >&2
    exit 6
fi
