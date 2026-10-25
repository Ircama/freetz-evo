$(call PKG_INIT_BIN, 2026-10-20)
$(PKG)_SOURCE:=cacert-$($(PKG)_VERSION).pem
$(PKG)_HASH:=796f1389bfea13c0ed78f663b765baaff54a508e5483786bd6ece73c5e3e3cbe
$(PKG)_SITE:=https://curl.se/ca,https://www.curl.se/ca,https://curl.haxx.se/ca
### WEBSITE:=https://www.curl.se/ca
### STEWARD:=fda77

$(PKG)_BINARY:=$($(PKG)_DIR)/cacert.pem
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/etc/ssl/certs/ca-bundle.crt

$(PKG)_STARTLEVEL=30


define $(PKG)_CUSTOM_UNPACK
	cp -fa $(DL_DIR)/$(CA_BUNDLE_SOURCE) $(CA_BUNDLE_BINARY)
endef

ifneq ($(strip $(DL_DIR)/$(CA_BUNDLE_SOURCE)), $(strip $(DL_DIR)/$(CA_BUNDLE_HOST_SOURCE)))
$(PKG_SOURCE_DOWNLOAD)
endif
$(PKG_UNPACKED)

$($(PKG)_BINARY): $($(PKG)_DIR)/.unpacked

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	$(INSTALL_FILE)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:

$(pkg)-uninstall:
	$(RM) $(CA_BUNDLE_TARGET_BINARY)

$(PKG_FINISH)
