$(call PKG_INIT_BIN, 6.6)
$(PKG)_SOURCE:=ncurses-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=355b4cbbed880b0381a04c46617b7656e362585d52e9cf84a67e2009b749ff11
$(PKG)_SITE:=@GNU/ncurses,https://invisible-island.net/archives/ncurses
### WEBSITE:=https://invisible-island.net/ncurses/
### MANPAGE:=https://invisible-island.net/ncurses/announce.html
### CHANGES:=https://invisible-island.net/ncurses/NEWS.html

$(PKG)_DEPENDS_ON += ncurses ncurses-host

# We build ncurses a second time (in a separate build dir) with --with-progs
# and only extract the tput/infocmp/clear/reset binaries.

$(PKG)_BINARY:=$($(PKG)_DIR)/progs/tput
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/tput

$(PKG)_BINARIES := tput
ifeq ($(strip $(FREETZ_PACKAGE_TPUT_infocmp)),y)
$(PKG)_BINARIES += infocmp
endif
ifeq ($(strip $(FREETZ_PACKAGE_TPUT_reset)),y)
$(PKG)_BINARIES += reset clear
endif

$(PKG)_CONFIGURE_ENV += cf_cv_func_nanosleep=yes
$(PKG)_CONFIGURE_ENV += cf_cv_link_dataonly=yes
$(PKG)_CONFIGURE_ENV += cf_cv_type_of_bool='unsigned char'
$(PKG)_CONFIGURE_ENV += cf_cv_working_poll=no

$(PKG)_CONFIGURE_OPTIONS += --enable-echo
$(PKG)_CONFIGURE_OPTIONS += --enable-const
$(PKG)_CONFIGURE_OPTIONS += --enable-overwrite
$(PKG)_CONFIGURE_OPTIONS += --disable-rpath
$(PKG)_CONFIGURE_OPTIONS += --disable-rpath-hack
$(PKG)_CONFIGURE_OPTIONS += --without-ada
$(PKG)_CONFIGURE_OPTIONS += --without-cxx
$(PKG)_CONFIGURE_OPTIONS += --without-cxx-binding
$(PKG)_CONFIGURE_OPTIONS += --without-debug
$(PKG)_CONFIGURE_OPTIONS += --without-profile
$(PKG)_CONFIGURE_OPTIONS += --with-progs
$(PKG)_CONFIGURE_OPTIONS += --without-manpages
$(PKG)_CONFIGURE_OPTIONS += --without-tests
$(PKG)_CONFIGURE_OPTIONS += --with-normal
$(PKG)_CONFIGURE_OPTIONS += --with-shared
$(PKG)_CONFIGURE_OPTIONS += --with-terminfo-dirs="/usr/share/terminfo"
$(PKG)_CONFIGURE_OPTIONS += --with-default-terminfo-dir="/usr/share/terminfo"
$(PKG)_CONFIGURE_OPTIONS += --disable-widec

ifneq ($(strip $(DL_DIR)/$(TPUT_SOURCE)), $(strip $(DL_DIR)/$(NCURSES_SOURCE)))
$(PKG_SOURCE_DOWNLOAD)
endif
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(TPUT_DIR) libs
	$(SUBMAKE) -C $(TPUT_DIR)/progs

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	$(INSTALL_BINARY_STRIP)
	@for prog in $(filter-out tput,$(TPUT_BINARIES)); do \
		if [ -f "$(TPUT_DIR)/progs/$$prog" ]; then \
			$(TARGET_STRIP) "$(TPUT_DIR)/progs/$$prog" -o "$(TPUT_DEST_DIR)/usr/bin/$$prog" 2>/dev/null || \
			install -m 0755 "$(TPUT_DIR)/progs/$$prog" "$(TPUT_DEST_DIR)/usr/bin/$$prog"; \
		fi; \
	done

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	-$(SUBMAKE) -C $(TPUT_DIR) clean
	$(RM) $(TPUT_DIR)/.configured

$(pkg)-uninstall:
	$(RM) $(TPUT_DEST_DIR)/usr/bin/tput
	$(RM) $(TPUT_DEST_DIR)/usr/bin/infocmp
	$(RM) $(TPUT_DEST_DIR)/usr/bin/reset
	$(RM) $(TPUT_DEST_DIR)/usr/bin/clear

$(PKG_FINISH)
