$(call PKG_INIT_BIN, 2.3.10)
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=3c4e6101ad53563f0a81f0041a30f26a9f8d143d97d46e3a1efbd7eab3d6be57
$(PKG)_SITE:=https://github.com/miniupnp/miniupnp/releases/download/miniupnpd_$(subst .,_,$($(PKG)_VERSION))
### WEBSITE:=https://miniupnp.tuxfamily.org/
### CHANGES:=https://github.com/miniupnp/miniupnp/releases
### CVSREPO:=https://github.com/miniupnp/miniupnp

$(PKG)_BINARY_BUILD_DIR:=$($(PKG)_DIR)
$(PKG)_BINARY:=$($(PKG)_BINARY_BUILD_DIR)/miniupnpd
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/sbin/miniupnpd

$(PKG)_DEPENDS_ON += iptables $(if $(FREETZ_TARGET_IPV6_SUPPORT),iptables)
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_MINIUPNPD_SECURE_MODE
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_MINIUPNPD_IPV6

# MiniUPnPd uses a custom configure script + Makefile.linux
# It does NOT use autotools

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)

$($(PKG)_DIR)/.configured: $($(PKG)_DIR)/.unpacked
	@$(call _ECHO,configuring)
	cd $(MINIUPNPD_BINARY_BUILD_DIR) && \
		$(TARGET_CONFIGURE_ENV) \
		OS_NAME=Linux OS_VERSION=$(call qstrip,$(FREETZ_KERNEL_VERSION)) \
		OS_MACHINE=mips FW=iptables \
		PKG_CONFIG_PATH="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig" \
		./configure
	@touch $@

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(MINIUPNPD_BINARY_BUILD_DIR) -f Makefile.linux \
		CC="$(TARGET_CC)" \
		CFLAGS="$(TARGET_CFLAGS) -Os -fno-strict-aliasing -fno-common" \
		CPPFLAGS="-D_GNU_SOURCE $(TARGET_CPPFLAGS)" \
		LDFLAGS="$(TARGET_LDFLAGS)" \
		STRIP="$(TARGET_STRIP)" \
		IPTABLESPATH="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr" \
		all

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	$(SUBMAKE) -C $(MINIUPNPD_BINARY_BUILD_DIR) -f Makefile.linux \
		DESTDIR="$(FREETZ_BASE_DIR)/$($(PKG)_TARGET_DIR)/root" \
		SBINDIR=/usr/sbin \
		ETCDIR=/etc \
		CONFIGDIR=/etc/default.miniupnpd \
		install
	# The install generates a UUID in the config; ensure freetz compatibility
	$(RM) $($(PKG)_DEST_DIR)/etc/default.miniupnpd/miniupnpd.conf
	$(INSTALL_FILE) $(MINIUPNPD_MAKE_DIR)/files/root/etc/default.miniupnpd/miniupnpd.conf \
		$($(PKG)_DEST_DIR)/etc/default.miniupnpd/miniupnpd.conf
	# Remove unnecessary files from install
	$(RM) -r $($(PKG)_DEST_DIR)/etc/default.miniupnpd/iptables_init.sh \
		$($(PKG)_DEST_DIR)/etc/default.miniupnpd/iptables_removeall.sh \
		$($(PKG)_DEST_DIR)/etc/default.miniupnpd/miniupnpd.8 \
		$($(PKG)_DEST_DIR)/etc/init.d

$(pkg):

$(pkg)-precompiled: \
	$(if $(FREETZ_PACKAGE_MINIUPNPD_DAEMON),$($(PKG)_TARGET_BINARY))

$(pkg)-clean:
	-$(SUBMAKE) -C $(MINIUPNPD_BINARY_BUILD_DIR) -f Makefile.linux clean

$(pkg)-uninstall:
	$(RM) $(MINIUPNPD_TARGET_BINARY)

$(PKG_FINISH)
