$(call PKG_INIT_BIN, 1.1.0)
### WEBSITE:=https://github.com/mandy321/Audiocular-Aura
### CHANGES:=
### CVSREPO:=

$(PKG)_CATEGORY:=Flasher tools

$(PKG)_DEPENDS_ON += hidapi
$(PKG)_DEPENDS_ON += libwebsockets

$(PKG)_BINARY_BUILD:=$($(PKG)_DIR)/aura-bridged
$(PKG)_BINARY_TARGET:=$($(PKG)_DEST_DIR)/usr/bin/aura-bridged

$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_AURAPEQ

$(PKG_LOCALSOURCE_PACKAGE)
$(PKG_CONFIGURED_NOP)

$($(PKG)_BINARY_BUILD): $($(PKG)_DIR)/.configured
	$(MAKE_ENV) $(TARGET_CC) $(TARGET_CFLAGS) $(TARGET_CPPFLAGS) $(TARGET_LDFLAGS) \
		-Wall -Wextra -Os -std=c11 \
		-D_DEFAULT_SOURCE -D_GNU_SOURCE \
		$(AURAPEQ_DIR)/aura-bridged.c \
		-o $@ \
		-lhidapi-hidraw -lwebsockets -lpthread

$($(PKG)_BINARY_TARGET): $($(PKG)_BINARY_BUILD)
	$(INSTALL_BINARY_STRIP)

$(pkg):

$(pkg)-precompiled: $($(PKG)_BINARY_TARGET)

$(pkg)-clean:
	$(RM) $($(PKG)_BINARY_BUILD)

$(pkg)-uninstall:
	$(RM) $($(PKG)_BINARY_TARGET)

$(PKG_FINISH)
