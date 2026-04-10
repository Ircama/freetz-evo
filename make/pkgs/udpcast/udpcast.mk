$(call PKG_INIT_BIN, 20250223)
$(PKG)_CATEGORY:=Data Migration and Disaster Recovery
$(PKG)_SOURCE:=udpcast_$($(PKG)_VERSION).orig.tar.gz
$(PKG)_HASH:=cefd7554c877e1bc76987d2b96b23f7699a2e5340c254454f61b6e0dae370aa7
$(PKG)_SITE:=https://deb.debian.org/debian/pool/main/u/udpcast
$(PKG)_DIR:=$(SOURCE_DIR)/udpcast-$($(PKG)_VERSION)
### WEBSITE:=https://udpcast.linux.lu/
### MANPAGE:=https://manpages.debian.org/udpcast
### CHANGES:=https://tracker.debian.org/pkg/udpcast

$(PKG)_BINARIES:=udp-sender udp-receiver
$(PKG)_BINARIES_BUILD_DIR:=$(addprefix $($(PKG)_DIR)/,$($(PKG)_BINARIES))
$(PKG)_BINARIES_TARGET_DIR:=$(addprefix $($(PKG)_DEST_DIR)/usr/sbin/,$($(PKG)_BINARIES))

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_BINARIES_BUILD_DIR): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(UDPCAST_DIR) V=1 all

$(foreach binary,$($(PKG)_BINARIES_BUILD_DIR),$(eval $(call INSTALL_BINARY_STRIP_RULE,$(binary),/usr/sbin)))

$(pkg):

$(pkg)-precompiled: $($(PKG)_BINARIES_TARGET_DIR)

$(pkg)-clean:
	-$(SUBMAKE) -C $(UDPCAST_DIR) clean

$(pkg)-uninstall:
	$(RM) $(UDPCAST_BINARIES:%=$(UDPCAST_DEST_DIR)/usr/sbin/%)

$(PKG_FINISH)
