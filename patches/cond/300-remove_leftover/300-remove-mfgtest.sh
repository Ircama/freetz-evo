[ "$FREETZ_AVM_HAS_MFGTEST_MODULE" == "y" ] || return 0
echo1 "removing *_mfgtest.ko"

rm_files $(find "${FILESYSTEM_MOD_DIR}/lib/modules" -name "*_mfgtest.ko")

