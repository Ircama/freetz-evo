$(call PKG_INIT_LIB, 6.3.0)
$(PKG)_LIB_VERSION:=13.3.2
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=082d999178291ed45ae24c3fd9e781120d3ec94d61d11121e5bac90c69365cda
$(PKG)_SITE:=https://www.lesbonscomptes.com/upmpdcli/downloads
### WEBSITE:=https://www.lesbonscomptes.com/upmpdcli/pages/downloads.html
### CHANGES:=https://framagit.org/medoc92/npupnp
### CVSREPO:=https://framagit.org/medoc92/npupnp

$(PKG)_BINARY:=$($(PKG)_DIR)/builddir/libnpupnp.so.$($(PKG)_LIB_VERSION)
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libnpupnp.so.$($(PKG)_LIB_VERSION)
$(PKG)_TARGET_BINARY:=$($(PKG)_TARGET_DIR)/libnpupnp.so.$($(PKG)_LIB_VERSION)

$(PKG)_DEPENDS_ON += meson-host
$(PKG)_DEPENDS_ON += curl
$(PKG)_DEPENDS_ON += libmicrohttpd

$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_IPV6_SUPPORT

$(PKG)_CONFIGURE_OPTIONS += -Dbuildtype=release
$(PKG)_CONFIGURE_OPTIONS += -Dipv6=$(if $(FREETZ_TARGET_IPV6_SUPPORT),true,false)
$(PKG)_CONFIGURE_OPTIONS += -Dwebserver=true
$(PKG)_CONFIGURE_OPTIONS += -Dtestmains=false
$(PKG)_CONFIGURE_OPTIONS += -Dexpat=disabled
$(PKG)_CONFIGURE_OPTIONS += -Dclient=true
$(PKG)_CONFIGURE_OPTIONS += -Ddevice=true
$(PKG)_CONFIGURE_OPTIONS += -Dsoap=true
$(PKG)_CONFIGURE_OPTIONS += -Dssdp=true
$(PKG)_CONFIGURE_OPTIONS += -Dgena=true
$(PKG)_CONFIGURE_OPTIONS += -Dtools=true
$(PKG)_CONFIGURE_OPTIONS += -Doptssdp=true
$(PKG)_CONFIGURE_OPTIONS += -Dunspecified_server=false

# Patch meson cross-file to fix tool paths
$(PKG)_CONFIGURE_PRE_CMDS += $(SED) -r -i \
	-e "s|^python[[:space:]]*=.*|python            = '$(abspath $(TOOLS_DIR)/path/python3)'|" \
	-e "s|^cmake[[:space:]]*=.*|cmake             = '$(abspath $(TOOLS_DIR)/path/cmake)'|" \
	meson.freetz;

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_MESON)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMESON) compile \
		-C $(LIBNPUPNP_DIR)/builddir/

$($(PKG)_STAGING_BINARY): $($(PKG)_BINARY)
	$(SUBMESON) install \
		--destdir "$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		-C $(LIBNPUPNP_DIR)/builddir/

$($(PKG)_TARGET_BINARY): $($(PKG)_STAGING_BINARY)
	$(INSTALL_LIBRARY_STRIP)

$(pkg): $($(PKG)_STAGING_BINARY)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBNINJA) -C $(LIBNPUPNP_DIR)/builddir/ clean
	$(RM) -r \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libnpupnp* \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/npupnp/ \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/libnpupnp*.pc

$(pkg)-uninstall:
	$(RM) $(LIBNPUPNP_TARGET_DIR)/libnpupnp.so*

$(PKG_FINISH)
