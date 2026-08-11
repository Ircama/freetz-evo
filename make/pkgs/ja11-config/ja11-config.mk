# Compiled with -std=c11, which requires GCC >= 4.7; the old GCC 4.6.4
# toolchain does not recognize the flag (error: unrecognized command line
# option '-std=c11'), so the package is gated on FREETZ_TARGET_GCC_4_7_MIN
# in Config.in. NOT a uClibc gate: uClibc 1.0.14 with GCC 5.5 builds fine
# (no regression on any uClibc >= 1.0.58 toolchain either).
$(call PKG_INIT_BIN, 1.0)
$(PKG)_SOURCE_DOWNLOAD_NAME:=1.0.tar.gz
$(PKG)_SOURCE:=$(pkg)-1.0.tar.gz
$(PKG)_HASH:=a1af2092417c7d53b23807cb1a3ec5d53f05318d38108e1c12e3f8c12e1ed988
$(PKG)_SITE:=https://github.com/Ircama/ja11-config/archive/refs/tags
### WEBSITE:=https://github.com/Ircama/ja11-config
### CHANGES:=https://github.com/Ircama/ja11-config/releases
### CVSREPO:=https://github.com/Ircama/ja11-config

$(PKG)_CATEGORY:=Flasher tools

$(PKG)_DEPENDS_ON += hidapi
$(PKG)_DEPENDS_ON += ncurses

$(PKG)_BINARY_BUILD:=$($(PKG)_DIR)/ja11-config-tui
$(PKG)_BINARY_TARGET:=$($(PKG)_DEST_DIR)/usr/bin/ja11-config-tui

$(PKG)_BINARY_JA11BOOT_BUILD:=$($(PKG)_DIR)/ja11-boot
$(PKG)_BINARY_JA11BOOT_TARGET:=$($(PKG)_DEST_DIR)/usr/bin/ja11-boot

$(PKG)_BINARY_JA11FLASH_BUILD:=$($(PKG)_DIR)/ja11-flash
$(PKG)_BINARY_JA11FLASH_TARGET:=$($(PKG)_DEST_DIR)/usr/bin/ja11-flash

$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_JA11_CONFIG

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_BINARY_BUILD): $($(PKG)_DIR)/.configured
	$(MAKE_ENV) $(TARGET_CC) $(TARGET_CFLAGS) $(TARGET_CPPFLAGS) $(TARGET_LDFLAGS) \
		-Wall -Wextra -Os -std=c11 \
		-D_DEFAULT_SOURCE -D_GNU_SOURCE \
		$(JA11_CONFIG_DIR)/ja11-config-tui.c \
		-o $@ \
		-lhidapi-libusb -lncurses -lm

$($(PKG)_BINARY_JA11BOOT_BUILD): $($(PKG)_DIR)/.configured
	$(MAKE_ENV) $(TARGET_CC) $(TARGET_CFLAGS) $(TARGET_CPPFLAGS) $(TARGET_LDFLAGS) \
		-Wall -Wextra -Os -std=c11 \
		-D_DEFAULT_SOURCE -D_GNU_SOURCE \
		$(JA11_CONFIG_DIR)/ja11-boot.c \
		-o $@ \
		-lhidapi-libusb

$($(PKG)_BINARY_JA11FLASH_BUILD): $($(PKG)_DIR)/.configured
	$(MAKE_ENV) $(TARGET_CC) $(TARGET_CFLAGS) $(TARGET_CPPFLAGS) $(TARGET_LDFLAGS) \
		-Wall -Wextra -Os -std=c11 \
		-D_DEFAULT_SOURCE -D_GNU_SOURCE \
		$(JA11_CONFIG_DIR)/ja11-flash.c \
		-o $@

$($(PKG)_BINARY_TARGET): $($(PKG)_BINARY_BUILD)
	$(INSTALL_BINARY_STRIP)

$($(PKG)_BINARY_JA11BOOT_TARGET): $($(PKG)_BINARY_JA11BOOT_BUILD)
	$(INSTALL_BINARY_STRIP)

$($(PKG)_BINARY_JA11FLASH_TARGET): $($(PKG)_BINARY_JA11FLASH_BUILD)
	$(INSTALL_BINARY_STRIP)

$(pkg):

$(pkg)-precompiled: $($(PKG)_BINARY_TARGET) $($(PKG)_BINARY_JA11BOOT_TARGET) $($(PKG)_BINARY_JA11FLASH_TARGET)

$(pkg)-clean:
	$(RM) $($(PKG)_BINARY_BUILD) $($(PKG)_BINARY_JA11BOOT_BUILD) $($(PKG)_BINARY_JA11FLASH_BUILD)

$(pkg)-uninstall:
	$(RM) $($(PKG)_BINARY_TARGET) $($(PKG)_BINARY_JA11BOOT_TARGET) $($(PKG)_BINARY_JA11FLASH_TARGET)

$(PKG_FINISH)
