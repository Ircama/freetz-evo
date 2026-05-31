$(call PKG_INIT_BIN, 0.14.0)
$(PKG)_SOURCE:=lnav-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=v$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=bf142441fc85e99c256ebe661e4199768acbd340da1344554da49a9e867a49ea
$(PKG)_SITE:=https://github.com/tstack/lnav/archive/refs/tags
### WEBSITE:=https://lnav.org/
### MANPAGE:=https://docs.lnav.org/
### CHANGES:=https://github.com/tstack/lnav/releases
### CVSREPO:=https://github.com/tstack/lnav

$(PKG)_BINARY:=$($(PKG)_DIR)/src/lnav
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/lnav

$(PKG)_DEPENDS_ON += zlib bzip2 curl libarchive libunistring ncursesw pcre2 sqlite
$(PKG)_DEPENDS_ON += $(STDCXXLIB)

# GitHub tag tarballs do not ship a generated configure script.
$(PKG)_CONFIGURE_PRE_CMDS += $(AUTORECONF)
$(PKG)_CONFIGURE_PRE_CMDS += $(call PKG_PREVENT_RPATH_HARDCODING,./configure)

$(PKG)_CONFIGURE_OPTIONS += --without-cargo
$(PKG)_CONFIGURE_OPTIONS += --disable-system-paths
$(PKG)_CONFIGURE_OPTIONS += --with-pcre2=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(LNAV_DIR)

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	$(INSTALL_BINARY_STRIP)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	@if [ -f "$(LNAV_DIR)/Makefile" ]; then \
		$(SUBMAKE) -C $(LNAV_DIR) clean; \
	fi

$(pkg)-uninstall:
	$(RM) $(LNAV_TARGET_BINARY)

$(PKG_FINISH)