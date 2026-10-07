[ -e "${FILESYSTEM_MOD_DIR}/usr/bin/bugreport-send" ] || [ -e "${FILESYSTEM_MOD_DIR}/etc/onlinechanged/bugreport-send" ] || return 0
echo1 "removing bugreport-send"

rm_files \
  "${FILESYSTEM_MOD_DIR}/usr/bin/bugreport-send" \
  "${FILESYSTEM_MOD_DIR}/etc/onlinechanged/bugreport-send"

