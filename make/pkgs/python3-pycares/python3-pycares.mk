$(call PKG_INIT_BIN, 5.0.1)
$(PKG)_SOURCE:=pycares-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=pycares-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/p/pycares
$(PKG)_HASH:=5a3c249c830432631439815f9a818463416f2a8cbdb1e988e78757de9ae75081
### WEBSITE:=https://github.com/saghul/pycares
### CHANGES:=https://github.com/saghul/pycares/releases
### CVSREPO:=https://github.com/saghul/pycares
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/pycares/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_PYCARES, , \
		CPATH="$(PYTHON3_STAGING_INC_DIR)" \
		CPPFLAGS="$(TARGET_CPPFLAGS) -I$(PYTHON3_STAGING_INC_DIR)" \
		CFLAGS="$(TARGET_CFLAGS) -I$(PYTHON3_STAGING_INC_DIR)" \
		CXXFLAGS="$(TARGET_CXXFLAGS) -I$(PYTHON3_STAGING_INC_DIR)" \
		LDFLAGS="$(TARGET_LDFLAGS) -L$(PYTHON3_STAGING_LIB_DIR)" \
	, isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_PYCARES_DIR)/.configured
	$(RM) -r $(PYTHON3_PYCARES_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_PYCARES_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/pycares \
		$(PYTHON3_PYCARES_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/pycares-*.dist-info

$(PKG_FINISH)
