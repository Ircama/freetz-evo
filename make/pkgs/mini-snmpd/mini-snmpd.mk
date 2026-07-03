$(call PKG_INIT_BIN,1.7)
$(PKG)_SOURCE:=mini-snmpd-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=bf119818276cd63e37d29d4c5e88f8cdf2975113bc9a2a39ee2b3a91f66de20a
$(PKG)_SITE:=https://github.com/troglobit/mini-snmpd/releases/download/v$($(PKG)_VERSION)
### WEBSITE:=https://troglobit.com/projects/mini-snmpd/
### MANPAGE:=https://ftp.troglobit.com/mini-snmpd/mini-snmpd.html
### CHANGES:=https://github.com/troglobit/mini-snmpd/releases
### CVSREPO:=https://github.com/troglobit/mini-snmpd

$(PKG)_BINARY:=$($(PKG)_DIR)/mini-snmpd
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/mini-snmpd

$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_IPV6_SUPPORT

$(PKG)_CONFIGURE_OPTIONS += $(if $(FREETZ_TARGET_IPV6_SUPPORT),--enable-ipv6,--disable-ipv6)


$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(MINI_SNMPD_DIR) \
		CC="$(TARGET_CC)" \
		STRIP="$(TARGET_STRIP)" \
		OFLAGS="$(TARGET_CFLAGS) $(MINI_SNMPD_CFLAGS)"

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	$(INSTALL_BINARY_STRIP)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	-$(SUBMAKE) -C $(MINI_SNMPD_DIR) clean

$(pkg)-uninstall:
	$(RM) $(MINI_SNMPD_TARGET_BINARY)

$(PKG_FINISH)
