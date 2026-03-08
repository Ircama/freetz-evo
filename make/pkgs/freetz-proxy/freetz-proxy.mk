$(call PKG_INIT_BIN, 0.1)
$(PKG)_BINARY:=$($(PKG)_DIR)/freetz_proxy
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/www/cgi-bin/freetz_proxy
# Symlink in the AVM "all" OEM cgi-bin so the web server can find the CGI
# without depending on fwmod's symlink-creation step.
$(PKG)_TARGET_SYMLINK:=$($(PKG)_DEST_DIR)/usr/www/all/cgi-bin/freetz_proxy

$(PKG_LOCALSOURCE_PACKAGE)
$(PKG_CONFIGURED_NOP)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(FREETZ_PROXY_DIR) \
		CC="$(TARGET_CC)" \
		CFLAGS="$(TARGET_CFLAGS)" \
		LDFLAGS="-static"

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	$(INSTALL_BINARY_STRIP)

$($(PKG)_TARGET_SYMLINK): $($(PKG)_TARGET_BINARY)
	mkdir -p $(dir $@)
	ln -sf /usr/www/cgi-bin/freetz_proxy $@

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY) $($(PKG)_TARGET_SYMLINK)

$(pkg)-clean:
	-$(SUBMAKE) -C $(FREETZ_PROXY_DIR) clean

$(pkg)-uninstall:
	$(RM) $(FREETZ_PROXY_TARGET_BINARY)
	$(RM) $($(PKG)_TARGET_SYMLINK)

$(PKG_FINISH)
