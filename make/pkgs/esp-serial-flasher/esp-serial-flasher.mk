$(call PKG_INIT_BIN, f1cccac82a41f6d494d953359d5ca2f5d70a9b12)
$(PKG)_SOURCE_DOWNLOAD_NAME:=$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=d31174f2cc06f60007c8da05078d902e4707286b20affcc0788c057aaa7b3d08
$(PKG)_SITE:=https://github.com/espressif/esp-serial-flasher/archive
### WEBSITE:=https://github.com/espressif/esp-serial-flasher
### CHANGES:=https://github.com/espressif/esp-serial-flasher/releases
### CVSREPO:=https://github.com/espressif/esp-serial-flasher

$(PKG)_CATEGORY_PKGS:=Flasher tools

$(PKG)_BINARY_GENERIC_BUILD:=$($(PKG)_DIR)/linux_flasher
$(PKG)_BINARY_GENERIC_TARGET:=$($(PKG)_DEST_DIR)/usr/bin/linux_flasher

$(PKG)_COMMON_CFLAGS:=\
	-I$($(PKG)_DIR)/include \
	-I$($(PKG)_DIR)/port \
	-I$($(PKG)_DIR)/private_include \
	-I$($(PKG)_DIR)/examples/common \
	-DSERIAL_FLASHER_DEBUG_TRACE=0 \
	-DSERIAL_FLASHER_RESET_HOLD_TIME_MS=100 \
	-DSERIAL_FLASHER_BOOT_HOLD_TIME_MS=50 \
	-DSERIAL_FLASHER_WRITE_BLOCK_RETRIES=3 \
	-DSERIAL_FLASHER_RESET_INVERT=0 \
	-DSERIAL_FLASHER_BOOT_INVERT=0

$(PKG)_COMMON_SOURCES:=\
	$($(PKG)_DIR)/src/*.c \
	$($(PKG)_DIR)/src/stubs/*.c \
	$($(PKG)_DIR)/port/linux_port.c \
	$($(PKG)_DIR)/examples/common/example_common.c

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_BINARY_GENERIC_BUILD): $($(PKG)_DIR)/.configured
	$(MAKE_ENV) $(TARGET_CC) $(TARGET_CFLAGS) $(TARGET_LDFLAGS) -Wall -Wextra -Os \
		$(ESP_SERIAL_FLASHER_COMMON_CFLAGS) \
		$(ESP_SERIAL_FLASHER_COMMON_SOURCES) \
		$(ESP_SERIAL_FLASHER_MAKE_DIR)/files/src/linux_flasher.c \
		-o $@

$($(PKG)_BINARY_GENERIC_TARGET): $($(PKG)_BINARY_GENERIC_BUILD)
	$(INSTALL_BINARY_STRIP)

$(pkg):

$(pkg)-precompiled: $($(PKG)_BINARY_GENERIC_TARGET)

$(pkg)-clean:
	$(RM) \
		$($(PKG)_BINARY_GENERIC_BUILD)

$(pkg)-uninstall:
	$(RM) \
		$($(PKG)_BINARY_GENERIC_TARGET)

$(PKG_FINISH)
