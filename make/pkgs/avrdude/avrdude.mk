$(call PKG_INIT_BIN, 8.1)
$(PKG)_SOURCE_DOWNLOAD_NAME:=v$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=2d3016edd5281ea09627c20b865e605d4f5354fe98f269ce20522a5b910ab399
$(PKG)_SITE:=https://github.com/avrdudes/avrdude/archive/refs/tags
### WEBSITE:=https://github.com/avrdudes/avrdude
### MANPAGE:=https://avrdudes.github.io/avrdude/
### CHANGES:=https://github.com/avrdudes/avrdude/releases
### CVSREPO:=https://github.com/avrdudes/avrdude

$(PKG)_CATEGORY_PKGS:=Flasher tools

$(PKG)_BINARY_BUILD:=$($(PKG)_DIR)/src/avrdude
$(PKG)_ELF2TAG_BUILD:=$($(PKG)_DIR)/src/elf2tag
$(PKG)_CONF_BUILD:=$($(PKG)_DIR)/src/avrdude.conf

$(PKG)_BINARY_TARGET:=$($(PKG)_DEST_DIR)/usr/bin/avrdude
$(PKG)_ELF2TAG_TARGET:=$($(PKG)_DEST_DIR)/usr/bin/elf2tag
$(PKG)_CONF_TARGET:=$($(PKG)_DEST_DIR)/etc/avrdude.conf

$(PKG)_DEPENDS_ON += cmake-host
$(PKG)_DEPENDS_ON += libelf libusb1 libftdi readline ncurses
# avrdude links the freetz-built libhidapi-libusb.so (found in the toolchain
# sysroot via PREFERRED_LIBHIDAPI) for USB HID programmers, so hidapi must be
# staged first. hidapi 0.15.0 with patch 003 uses only pthread_mutex/cond,
# so this stays compatible with old uClibc (0.9.32.1/3270v3) and modern ones.
$(PKG)_DEPENDS_ON += hidapi

$(PKG)_REBUILD_SUBOPTS += $(LIBELF_REBUILD_SUBOPTS)
$(PKG)_REBUILD_SUBOPTS += $(LIBUSB1_REBUILD_SUBOPTS)
$(PKG)_REBUILD_SUBOPTS += $(LIBFTDI_REBUILD_SUBOPTS)
$(PKG)_REBUILD_SUBOPTS += $(READLINE_REBUILD_SUBOPTS)
$(PKG)_REBUILD_SUBOPTS += $(NCURSES_REBUILD_SUBOPTS)

$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_INSTALL_PREFIX="/usr"
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_SKIP_RPATH=YES
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_BUILD_TYPE=Release
$(PKG)_CONFIGURE_OPTIONS += -DBUILD_DOC=OFF
$(PKG)_CONFIGURE_OPTIONS += -DBUILD_SHARED_LIBS=OFF
$(PKG)_CONFIGURE_OPTIONS += -DFORCE_DISABLE_PYTHON_SUPPORT=ON
$(PKG)_CONFIGURE_OPTIONS += -DHAVE_LINUXGPIO=OFF
$(PKG)_CONFIGURE_OPTIONS += -DHAVE_LINUXSPI=OFF
$(PKG)_CONFIGURE_OPTIONS += -DHAVE_PARPORT=OFF
$(PKG)_CONFIGURE_OPTIONS += -DUSE_EXTERNAL_LIBS=OFF

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CMAKE)

$($(PKG)_BINARY_BUILD): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(AVRDUDE_DIR)

$($(PKG)_BINARY_TARGET): $($(PKG)_BINARY_BUILD)
	$(INSTALL_BINARY_STRIP)

$($(PKG)_ELF2TAG_TARGET): $($(PKG)_ELF2TAG_BUILD)
	$(INSTALL_FILE)

$($(PKG)_CONF_TARGET): $($(PKG)_BINARY_BUILD)
	@if [ -r "$(AVRDUDE_CONF_BUILD)" ]; then \
		mkdir -p $(dir $@); \
		cp "$(AVRDUDE_CONF_BUILD)" $@; \
	elif [ -r "$(AVRDUDE_DIR)/avrdude.conf" ]; then \
		mkdir -p $(dir $@); \
		cp "$(AVRDUDE_DIR)/avrdude.conf" $@; \
	else \
		echo "ERROR: avrdude.conf not found in build tree"; \
		exit 1; \
	fi

$(pkg):

$(pkg)-precompiled: $($(PKG)_BINARY_TARGET) $($(PKG)_ELF2TAG_TARGET) $($(PKG)_CONF_TARGET)

$(pkg)-clean:
	-$(SUBMAKE) -C $(AVRDUDE_DIR) clean

$(pkg)-uninstall:
	$(RM) $($(PKG)_BINARY_TARGET) $($(PKG)_ELF2TAG_TARGET) $($(PKG)_CONF_TARGET)

$(PKG_FINISH)