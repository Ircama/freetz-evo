$(call TOOLS_INIT, 1.4.1)
# Update libs/ too !
$(PKG)_SOURCE:=mpc-$($(PKG)_VERSION).tar.xz
$(PKG)_HASH:=91204cd32f164bd3b7c992d4a6a8ce6519511aadab30f78b6982d0bf8d73e931
$(PKG)_SITE:=@GNU/mpc
### WEBSITE:=https://www.multiprecision.org/
### MANPAGE:=https://www.multiprecision.org/mpc/documentation.html
### CHANGES:=https://ftp.gnu.org/gnu/mpc/
### CVSREPO:=https://gitlab.inria.fr/mpc/mpc
### STEWARD:=fda77

$(PKG)_DEPENDS_ON+=gmp-host
$(PKG)_DEPENDS_ON+=mpfr-host

$(PKG)_BINARY:=$(HOST_TOOLS_DIR)/lib/libmpc.a

$(PKG)_CONFIGURE_ENV += CC="$(TOOLCHAIN_HOSTCC)"
$(PKG)_CONFIGURE_ENV += CFLAGS="$(TOOLCHAIN_HOST_CFLAGS)"

$(PKG)_CONFIGURE_OPTIONS += --prefix=$(HOST_TOOLS_DIR)
$(PKG)_CONFIGURE_OPTIONS += --build=$(GNU_HOST_NAME)
$(PKG)_CONFIGURE_OPTIONS += --host=$(GNU_HOST_NAME)
$(PKG)_CONFIGURE_OPTIONS += --disable-shared
$(PKG)_CONFIGURE_OPTIONS += --enable-static
$(PKG)_CONFIGURE_OPTIONS += --with-gmp=$(HOST_TOOLS_DIR)
$(PKG)_CONFIGURE_OPTIONS += --with-mpfr=$(HOST_TOOLS_DIR)


$(TOOLS_SOURCE_DOWNLOAD)
$(TOOLS_UNPACKED)
$(TOOLS_CONFIGURED_CONFIGURE)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured | $(HOST_TOOLS_DIR)
	$(TOOLS_SUBMAKE) -C $(MPC_HOST_DIR) install

$(pkg)-precompiled: $($(PKG)_BINARY)


$(pkg)-clean:
	-$(MAKE) -C $(MPC_HOST_DIR) clean

$(pkg)-dirclean:
	$(RM) -r $(MPC_HOST_DIR)

$(pkg)-distclean: $(pkg)-dirclean
	$(RM) $(HOST_TOOLS_DIR)/lib/libmpc* $(HOST_TOOLS_DIR)/include/*mpc*.h

$(TOOLS_FINISH)
