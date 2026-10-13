$(call PKG_INIT_BIN, 0.2.0)
$(PKG)_SOURCE:=android_backup-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=android_backup-0.2.0.tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/a/android_backup
$(PKG)_HASH:=864b6a9f8e2dda7a3af3726df7439052d35781c5f7d50dd771d709293d158b97
### WEBSITE:=https://pypi.org/project/android_backup/
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/android_backup/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_ANDROID_BACKUP, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	$(RM) $(PYTHON3_ANDROID_BACKUP_DIR)/.configured
	$(RM) -r $(PYTHON3_ANDROID_BACKUP_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_ANDROID_BACKUP_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/android_backup \
		$(PYTHON3_ANDROID_BACKUP_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/android-backup-*.dist-info

$(PKG_FINISH)
