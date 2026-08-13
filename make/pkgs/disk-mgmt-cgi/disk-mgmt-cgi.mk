$(call PKG_INIT_BIN, 1.0)
$(PKG)_CATEGORY_PKGS:=Web interfaces

# disk-mgmt-cgi requires uClibc 1.0.58 or newer: it depends on partclone
# (and other modern disk tools), which need libblkid from util-linux 2.41.
# The option is gated by "depends on FREETZ_TARGET_UCLIBC_1_0_58_MIN" in
# Config.in.

$(PKG_UNPACKED)

$(pkg):

$(pkg)-precompiled:

$(pkg)-clean:

$(PKG_FINISH)
