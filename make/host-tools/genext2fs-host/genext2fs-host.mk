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

$(PKG)_CONFIGURE_PRE_CMDS += ./autogen.sh;
$(PKG)_CONFIGURE_OPTIONS += --program-prefix=""
$(PKG)_CONFIGURE_OPTIONS += --program-suffix=""
$(PKG)_CONFIGURE_OPTIONS += --prefix=$(FREETZ_BASE_DIR)/$(TOOLS_DIR)


$(TOOLS_SOURCE_DOWNLOAD)
$(TOOLS_UNPACKED)
$(TOOLS_CONFIGURED_CONFIGURE)

$($(PKG)_DIR)/genext2fs: $($(PKG)_DIR)/.configured
	$(TOOLS_SUBMAKE) CC="$(TOOLS_CC)" CXX="$(TOOLS_CXX)" CFLAGS="$(TOOLS_CFLAGS)" LDFLAGS="$(TOOLS_LDFLAGS)" -C $(GENEXT2FS_HOST_DIR) all
	touch -c $@

$(pkg)-test: $($(PKG)_DIR)/.tests-passed
$($(PKG)_DIR)/.tests-passed: $($(PKG)_DIR)/genext2fs
	(cd $(GENEXT2FS_HOST_DIR); ./test.sh)
	touch $@

$(TOOLS_DIR)/genext2fs: $($(PKG)_DIR)/genext2fs
	$(INSTALL_FILE)

$(pkg)-precompiled: $(TOOLS_DIR)/genext2fs


$(pkg)-clean:
	-$(MAKE) -C $(GENEXT2FS_HOST_DIR) clean
	$(RM) $(GENEXT2FS_HOST_DIR)/.configured $(GENEXT2FS_HOST_DIR)/.tests-passed

$(pkg)-dirclean:
	$(RM) -r $(GENEXT2FS_HOST_DIR)

$(pkg)-distclean: $(pkg)-dirclean
	$(RM) $(TOOLS_DIR)/genext2fs

$(TOOLS_FINISH)
