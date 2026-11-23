[ "$FREETZ_REMOVE_ASSETSD" == "y" ] || return 0
echo1 "removing assetsd"

modsed -r \
  's/(AVMDAEMONS.*) assetsd([ "])/\1\2/g' \
  "${FILESYSTEM_MOD_DIR}/etc/init.d/rc.net"

supervisor_delete_service "assetsd"

rm_files ${FILESYSTEM_MOD_DIR}/sbin/assetsd

