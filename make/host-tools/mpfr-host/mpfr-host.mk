$(call TOOLS_INIT, 4.2.2)
# Update libs/ too !
$(PKG)_SOURCE:=mpfr-$($(PKG)_VERSION).tar.xz
$(PKG)_HASH:=b67ba0383ef7e8a8563734e2e889ef5ec3c3b898a01d00fa0a6869ad81c6ce01
$(PKG)_SITE:=http://www.mpfr.org/mpfr-$($(PKG)_VERSION)
### WEBSITE:=https://www.mpfr.org/
### MANPAGE:=https://www.mpfr.org/faq.html
### CHANGES:=https://ftp.gnu.org/gnu/mpfr/
### CVSREPO:=https://gitlab.inria.fr/mpfr/mpfr
### STEWARD:=fda77

$(PKG)_DEPENDS_ON+=gmp-host

$(PKG)_BINARY:=$(HOST_TOOLS_DIR)/lib/libmpfr.a

$(PKG)_CONFIGURE_ENV += CC="$(TOOLCHAIN_HOST_CC)"
$(PKG)_CONFIGURE_ENV += CFLAGS="$(TOOLCHAIN_HOST_CFLAGS)"

$(PKG)_CONFIGURE_OPTIONS += --prefix=$(HOST_TOOLS_DIR)
$(PKG)_CONFIGURE_OPTIONS += --build=$(GNU_HOST_NAME)
$(PKG)_CONFIGURE_OPTIONS += --host=$(GNU_HOST_NAME)
$(PKG)_CONFIGURE_OPTIONS += --disable-shared
$(PKG)_CONFIGURE_OPTIONS += --enable-static
$(PKG)_CONFIGURE_OPTIONS += --with-gmp=$(HOST_TOOLS_DIR)


$(TOOLS_SOURCE_DOWNLOAD)
$(TOOLS_UNPACKED)
$(TOOLS_CONFIGURED_CONFIGURE)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured | $(HOST_TOOLS_DIR)
	$(TOOLS_SUBMAKE) -C $(MPFR_HOST_DIR)/src install

$(pkg)-precompiled: $($(PKG)_BINARY)


$(pkg)-clean:
	-$(MAKE) -C $(MPFR_HOST_DIR) clean

$(pkg)-dirclean:
	$(RM) -r $(MPFR_HOST_DIR)

$(pkg)-distclean: $(pkg)-dirclean
	$(RM) $(HOST_TOOLS_DIR)/lib/libmpfr* $(HOST_TOOLS_DIR)/include/*mpfr*.h

$(TOOLS_FINISH)
