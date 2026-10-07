$(call PKG_INIT_BIN, 2026-09-25)
$(PKG)_SOURCE:=cacert-$($(PKG)_VERSION).pem
$(PKG)_HASH:=a41b5d356aea97a529fe27e0f7316d2f9d946d75927476cf9cf1b90637d00505
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
