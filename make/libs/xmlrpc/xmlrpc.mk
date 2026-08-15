$(call PKG_INIT_LIB, 1.64.03)
$(PKG)_SOURCE:=xmlrpc-$($(PKG)_VERSION).tgz
$(PKG)_HASH:=74729d364edbedbe42e782822da1e076f3f45c65c4278a3cfba5f2342d7cedbe
$(PKG)_SITE:=https://downloads.sourceforge.net/project/xmlrpc-c/Xmlrpc-c%20Super%20Stable/$($(PKG)_VERSION)
$(PKG)_DIR:=$(SOURCE_DIR)/xmlrpc-$($(PKG)_VERSION)
### WEBSITE:=http://xmlrpc-c.sourceforge.net/
### MANPAGE:=http://xmlrpc-c.sourceforge.net/doc/
### CHANGES:=https://sourceforge.net/projects/xmlrpc-c/files/
### CVSREPO:=https://sourceforge.net/p/xmlrpc-c/code/
### SUPPORT:=Ircama

$(PKG)_CATEGORY_LIBS:=XML & XSLT

# xmlrpc-c provides multiple libraries
$(PKG)_LIBS_SHORT := xmlrpc xmlrpc_server xmlrpc_server_abyss xmlrpc_server_cgi xmlrpc_client xmlrpc_abyss xmlrpc_util xmlrpc_xmlparse xmlrpc_xmltok

# Single build sentinel: used to track whether the build step has run.
# The 4 internal libs (abyss, util, xmlparse, xmltok) are built in lib/
# subdirectories, not in src/, so they cannot be used as sentinel targets.
$(PKG)_BINARY := $($(PKG)_DIR)/src/libxmlrpc.so
$(PKG)_LIBS_STAGING := $($(PKG)_LIBS_SHORT:%=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/lib%.so)
$(PKG)_LIBS_TARGET := $($(PKG)_LIBS_SHORT:%=$($(PKG)_TARGET_DIR)/lib%.so)

$(PKG)_DEPENDS_ON += curl expat gennmtab-host

$(PKG)_CONFIGURE_OPTIONS += --enable-shared
$(PKG)_CONFIGURE_OPTIONS += --enable-static
$(PKG)_CONFIGURE_OPTIONS += --disable-libxml2-backend
$(PKG)_CONFIGURE_OPTIONS += --disable-wininet-client
$(PKG)_CONFIGURE_OPTIONS += --disable-cplusplus

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)

# Preserve library context for SUBMAKE-driven build/install output.
$($(PKG)_BINARY): PKG_TYPE:=LIB
$($(PKG)_BINARY): pkg:=$(pkg)
$($(PKG)_LIBS_STAGING): PKG_TYPE:=LIB
$($(PKG)_LIBS_STAGING): pkg:=$(pkg)

$($(PKG)_DIR)/.configured: $($(PKG)_DIR)/.unpacked
	(cd $(XMLRPC_DIR); $(RM) -r config.cache; \
		$(TARGET_CONFIGURE_ENV) \
		AR="$(TARGET_AR)" \
		RANLIB="$(TARGET_RANLIB)" \
		./configure \
			--build=$(GNU_HOST_NAME) \
			--host=$(GNU_TARGET_NAME) \
			--target=$(GNU_TARGET_NAME) \
			--prefix=/usr \
			$($(PKG)_CONFIGURE_OPTIONS) && \
		find . -name Makefile -exec sed -i \
			-e "s|../gennmtab/gennmtab|$(abspath $(TOOLS_DIR))/gennmtab|g" \
			-e "s|GENNMTAB = tools/gennmtab|GENNMTAB = $(abspath $(TOOLS_DIR))/gennmtab|g" \
			{} \; \
	) $(SILENT)
	touch $@

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(XMLRPC_DIR) -j1

$($(PKG)_LIBS_STAGING): $($(PKG)_BINARY)
	$(SUBMAKE) -C $(XMLRPC_DIR) \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install
	# Fix xmlrpc-c-config to use sysroot paths
	sed -i \
		-e 's|HEADERINST_DIR="/usr/include"|HEADERINST_DIR="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include"|' \
		-e 's|LIBINST_DIR="/usr/lib"|LIBINST_DIR="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib"|' \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin/xmlrpc-c-config

$($(PKG)_LIBS_TARGET): $($(PKG)_TARGET_DIR)/lib%.so: $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/lib%.so
	$(INSTALL_LIBRARY_STRIP)

$(pkg): $($(PKG)_LIBS_STAGING)

$(pkg)-precompiled: $($(PKG)_LIBS_TARGET)


$(pkg)-clean:
	-[ -d $(XMLRPC_DIR) ] && $(MAKE) -C $(XMLRPC_DIR) clean $(SILENT)
	$(RM) $($(PKG)_BINARY)
	$(RM) -r $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libxmlrpc* \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/xmlrpc* \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin/xmlrpc-c-config

$(pkg)-uninstall:
	$(RM) $($(PKG)_LIBS_TARGET)

$(PKG_FINISH)
