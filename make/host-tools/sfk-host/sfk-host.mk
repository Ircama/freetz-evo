$(call TOOLS_INIT, 2.0.0.3)
$(PKG)_SOURCE_DOWNLOAD_NAME:=$(pkg_short)-$(call GET_MAJOR_VERSION,$($(PKG)_VERSION),3).tar.gz
$(PKG)_SOURCE:=$(pkg_short)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=b7e2e3848e3126dcee916056bff5f8340acae9158f3610049de2cde999ccca63
$(PKG)_SITE:=@SF/swissfileknife
### WEBSITE:=https://www.stahlworks.com/sfk
### MANPAGE:=https://www.stahlworks.com/dev/swiss-file-knife.html
### CHANGES:=https://sourceforge.net/p/swissfileknife/news/
### CVSREPO:=https://sourceforge.net/projects/swissfileknife/files/1-swissfileknife/
### STEWARD:=fda77

$(PKG)_BINARY:=$($(PKG)_DIR)/sfk
$(PKG)_TARGET_BINARY:=$(TOOLS_DIR)/sfk

$(PKG)_CXXFLAGS := $(TOOLS_CFLAGS)
$(PKG)_CXXFLAGS += -w


$(TOOLS_SOURCE_DOWNLOAD)
$(TOOLS_UNPACKED)
$(TOOLS_CONFIGURED_CONFIGURE)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(TOOLS_SUBMAKE) -C $(SFK_HOST_DIR) \
		CXXFLAGS="$(SFK_HOST_CXXFLAGS)" \
		all

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	$(INSTALL_FILE)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	-$(MAKE) -C $(SFK_HOST_DIR) clean

$(pkg)-dirclean:
	$(RM) -r $(SFK_HOST_DIR)

$(pkg)-distclean: $(pkg)-dirclean
	$(RM) $(SFK_HOST_TARGET_BINARY)

$(TOOLS_FINISH)
