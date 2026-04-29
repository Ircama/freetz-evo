$(call PKG_INIT_BIN, 7.2.2)
$(PKG)_SOURCE:=psutil-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=psutil-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/p/psutil
$(PKG)_HASH:=0746f5f8d406af344fd547f1c8daa5f5c33dbc293bb8d6a16d80b4bb88f59372
### WEBSITE:=https://github.com/giampaolo/psutil
### CHANGES:=https://github.com/giampaolo/psutil/releases
### CVSREPO:=https://github.com/giampaolo/psutil
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/psutil/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_PSUTIL, , \
		CPATH="$(PYTHON3_STAGING_INC_DIR)" \
		CPPFLAGS="$(TARGET_CPPFLAGS) -I$(PYTHON3_STAGING_INC_DIR)" \
		CFLAGS="$(TARGET_CFLAGS) -I$(PYTHON3_STAGING_INC_DIR)" \
		CXXFLAGS="$(TARGET_CXXFLAGS) -I$(PYTHON3_STAGING_INC_DIR)" \
		LDFLAGS="$(TARGET_LDFLAGS) -L$(PYTHON3_STAGING_LIB_DIR)" \
	, isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_PSUTIL_DIR)/.configured
	$(RM) -r $(PYTHON3_PSUTIL_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_PSUTIL_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/psutil \
		$(PYTHON3_PSUTIL_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/psutil-*.dist-info

$(PKG_FINISH)
