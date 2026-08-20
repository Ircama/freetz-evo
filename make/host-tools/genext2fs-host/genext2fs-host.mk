$(call TOOLS_INIT, 1.6.2)
$(PKG)_SOURCE_DOWNLOAD_NAME:=v$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=genext2fs-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=b8aba9af48e664fa60134af696a57b3bb4ebd2b2878533d7611734e90b883ecc
$(PKG)_SITE:=https://github.com/bestouff/genext2fs/archive/refs/tags
### WEBSITE:=https://genext2fs.sourceforge.net/
### MANPAGE:=https://sourceforge.net/projects/genext2fs/
### CHANGES:=https://github.com/bestouff/genext2fs/tags
### CVSREPO:=https://github.com/bestouff/genext2fs
### STEWARD:=fda77

$(PKG)_BINARY:=$($(PKG)_DIR)/genext2fs
$(PKG)_TARGET_BINARY:=$(TOOLS_DIR)/genext2fs

$(PKG)_CONFIGURE_PRE_CMDS += ./autogen.sh;
$(PKG)_CONFIGURE_OPTIONS += --program-prefix=""
$(PKG)_CONFIGURE_OPTIONS += --program-suffix=""


$(TOOLS_SOURCE_DOWNLOAD)
$(TOOLS_UNPACKED)
$(TOOLS_CONFIGURED_CONFIGURE)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(TOOLS_SUBMAKE) -C $(GENEXT2FS_HOST_DIR) \
		CC="$(TOOLS_CC)" \
		CXX="$(TOOLS_CXX)" \
		CFLAGS="$(TOOLS_CFLAGS)" \
		LDFLAGS="$(TOOLS_LDFLAGS)" \
		all
	touch -c $@

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	$(INSTALL_FILE)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


.PHONY: $(pkg)-test
$(pkg)-test: $($(PKG)_BINARY)
	(cd $(GENEXT2FS_HOST_DIR) && ./test.sh)


$(pkg)-clean:
	-$(MAKE) -C $(GENEXT2FS_HOST_DIR) clean
	$(RM) $(GENEXT2FS_HOST_DIR)/.configured

$(pkg)-dirclean:
	$(RM) -r $(GENEXT2FS_HOST_DIR)

$(pkg)-distclean: $(pkg)-dirclean
	$(RM) $(GENEXT2FS_HOST_TARGET_BINARY)

$(TOOLS_FINISH)
