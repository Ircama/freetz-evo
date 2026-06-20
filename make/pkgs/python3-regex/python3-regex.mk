$(call PKG_INIT_BIN, 2026.5.9)
$(PKG)_SOURCE:=regex-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=regex-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/r/regex
$(PKG)_HASH:=a8234aa23ec39894bfe4a3f1b85616a7032481964a13ac6fc9f10de4f6fca270
### WEBSITE:=https://github.com/mrabarnett/mrab-regex
### CHANGES:=https://github.com/mrabarnett/mrab-regex/issues
### CVSREPO:=https://github.com/mrabarnett/mrab-regex
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-setuptools-host

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/regex/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/PKG, PYTHON3_REGEX, , )

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_REGEX_DIR)/.configured
	$(RM) -r $(PYTHON3_REGEX_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_REGEX_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/regex \
		$(PYTHON3_REGEX_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/regex-*.dist-info

$(PKG_FINISH)
