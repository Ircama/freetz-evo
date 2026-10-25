$(call PKG_INIT_BIN, 1.7.1)
$(PKG)_SOURCE:=bridge-utils-$($(PKG)_VERSION).tar.xz
$(PKG)_HASH:=a61d8be4f1a1405c60c8ef38d544f0c18c05b33b9b07e5b4b31033536165e60e
$(PKG)_SITE:=@KERNEL/linux/utils/net/bridge-utils
### WEBSITE:=https://wiki.linuxfoundation.org/networking/bridge
### MANPAGE:=https://linux.die.net/man/8/brctl
### CHANGES:=https://www.kernel.org/pub/linux/utils/net/bridge-utils/
### CVSREPO:=https://git.kernel.org/pub/scm/network/bridge/bridge-utils.git/

$(PKG)_BINARY:=$($(PKG)_DIR)/brctl/brctl
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/sbin/brctl

# TODO: check if this package really requires internal kernel headers
#       I doubt this is the case as the following path is relative,
#       i.e. doesn't really point to the kernel headers dir while
#       package is being built
#$(PKG)_REBUILD_SUBOPTS += FREETZ_KERNEL_VERSION

$(PKG)_CONFIGURE_PRE_CMDS += $(AUTORECONF)

$(PKG)_CONFIGURE_OPTIONS += --with-linux-headers=$(KERNEL_SOURCE_DIR)/include


$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(BRIDGE_UTILS_DIR)

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	$(INSTALL_BINARY_STRIP)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	-$(SUBMAKE) -C $(BRIDGE_UTILS_DIR) clean

$(pkg)-uninstall:
	$(RM) $(BRIDGE_UTILS_TARGET_BINARY)

$(PKG_FINISH)
