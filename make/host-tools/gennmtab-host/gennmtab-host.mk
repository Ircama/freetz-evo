$(call TOOLS_INIT, 1.64.03)
$(PKG)_SOURCE:=xmlrpc-$($(PKG)_VERSION).tgz
$(PKG)_HASH:=74729d364edbedbe42e782822da1e076f3f45c65c4278a3cfba5f2342d7cedbe
$(PKG)_SITE:=https://downloads.sourceforge.net/project/xmlrpc-c/Xmlrpc-c%20Super%20Stable/$($(PKG)_VERSION)
$(PKG)_DIR:=$($(PKG)_SOURCE_DIR)/xmlrpc-$($(PKG)_VERSION)
### WEBSITE:=http://xmlrpc-c.sourceforge.net/
### CHANGES:=https://sourceforge.net/projects/xmlrpc-c/files/
### CVSREPO:=https://sourceforge.net/p/xmlrpc-c/code/
### SUPPORT:=Ircama

$(PKG)_BINARY:=$($(PKG)_DIR)/lib/expat/gennmtab/gennmtab
$(PKG)_TARGET_BINARY:=$(TOOLS_DIR)/gennmtab


$(TOOLS_SOURCE_DOWNLOAD)
$(TOOLS_UNPACKED)
$(TOOLS_CONFIGURED_NOP)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	(cd $(GENNMTAB_HOST_DIR) && \
		./configure \
			--prefix=/usr \
			--disable-libxml2-backend \
			--disable-wininet-client \
			--disable-curl-client \
			--disable-cplusplus \
	) $(SILENT)
	$(TOOLS_SUBMAKE) -C $(GENNMTAB_HOST_DIR)/lib/expat/gennmtab gennmtab

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	$(INSTALL_FILE)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	-$(MAKE) -C $(GENNMTAB_HOST_DIR)/lib/expat/gennmtab clean
	$(RM) $(GENNMTAB_HOST_DIR)/.configured

$(pkg)-dirclean:
	$(RM) -r $(GENNMTAB_HOST_DIR)

$(pkg)-distclean: $(pkg)-dirclean
	$(RM) $(GENNMTAB_HOST_TARGET_BINARY)

$(TOOLS_FINISH)
