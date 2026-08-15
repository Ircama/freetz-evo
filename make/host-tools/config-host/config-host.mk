$(call TOOLS_INIT, 428664896cf9e92d264976a960c76660938dffce)
$(PKG)_SOURCE:=$(pkg_short)-$($(PKG)_VERSION).tar.xz
$(PKG)_HASH:=c1760d9a2a7d6bbe87031bc0c7570226feb46f1f4da8b11fd72cb6ef0d40c5aa
$(PKG)_SITE:=git@https://https.git.savannah.gnu.org/git/config.git
#$(PKG)_SITE:=https://cgit.git.savannah.gnu.org/cgit/config.git/snapshot
### VERSION:=4286648
### WEBSITE:=https://savannah.gnu.org/projects/config
### CHANGES:=https://cgit.git.savannah.gnu.org/cgit/config.git/log/
### CVSREPO:=https://cgit.git.savannah.gnu.org/cgit/config.git
### STEWARD:=fda77

$(PKG)_DESTDIR             := $(FREETZ_BASE_DIR)/$(TOOLS_BUILD_DIR)

$(PKG)_BINARIES            := config.guess config.sub
$(PKG)_BINARIES_BUILD_DIR  := $($(PKG)_BINARIES:%=$($(PKG)_DIR)/%)
$(PKG)_BINARIES_TARGET_DIR := $($(PKG)_BINARIES:%=$($(PKG)_DESTDIR)/etc/%)


$(TOOLS_SOURCE_DOWNLOAD)
$(TOOLS_UNPACKED)
$(TOOLS_CONFIGURED_NOP)

$($(PKG)_BINARIES_BUILD_DIR): $($(PKG)_DIR)/.configured
	@touch -c $@

$($(PKG)_BINARIES_TARGET_DIR): $($(PKG)_DESTDIR)/etc/%: $($(PKG)_DIR)/%
	$(INSTALL_FILE)

$(pkg)-precompiled: $($(PKG)_BINARIES_TARGET_DIR)


$(pkg)-clean:
	$(RM) $(CONFIG_HOST_DIR)/.{configured}

$(pkg)-dirclean:
	$(RM) -r $(CONFIG_HOST_DIR)

$(pkg)-distclean: $(pkg)-dirclean
	$(RM) $(CONFIG_HOST_BINARIES_TARGET_DIR)

$(TOOLS_FINISH)
