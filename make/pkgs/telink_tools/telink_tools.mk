$(call PKG_INIT_BIN, 1.0)
### WEBSITE:=https://github.com/Ircama/freetz-ble
### CHANGES:=
### CVSREPO:=

$(PKG)_CATEGORY:=Flasher tools

$(PKG)_BINARY_BUILD:=$($(PKG)_DIR)/telink_tools
$(PKG)_BINARY_TARGET:=$($(PKG)_DEST_DIR)/usr/bin/telink_tools

$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_TELINK_TOOLS

$(PKG_LOCALSOURCE_PACKAGE)
$(PKG_CONFIGURED_NOP)

$($(PKG)_BINARY_BUILD): $($(PKG)_DIR)/.configured
	$(MAKE_ENV) $(TARGET_CC) $(TARGET_CFLAGS) $(TARGET_LDFLAGS) -Wall -Wextra -Os \
		$(TELINK_TOOLS_DIR)/telink_tools.c \
		-o $@

$($(PKG)_BINARY_TARGET): $($(PKG)_BINARY_BUILD)
	$(INSTALL_BINARY_STRIP)

$(pkg):

$(pkg)-precompiled: $($(PKG)_BINARY_TARGET)

$(pkg)-clean:
	$(RM) $($(PKG)_BINARY_BUILD)

$(pkg)-uninstall:
	$(RM) $($(PKG)_BINARY_TARGET)

$(PKG_FINISH)