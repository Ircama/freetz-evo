$(call PKG_INIT_BIN, 3.27.0)
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.bz2
$(PKG)_HASH:=5b5937de8257ee8f51698ea71b9711adce98061aa07daa4a685efc3af9215bef
$(PKG)_SITE:=https://sourceware.org/pub/valgrind
### WEBSITE:=https://valgrind.org/
### MANPAGE:=https://valgrind.org/docs/manual/manual.html
### CHANGES:=https://valgrind.org/docs/manual/dist.news.html
### CVSREPO:=https://sourceware.org/git/?p=valgrind.git

$(PKG)_CATEGORY:=Debug helpers

$(PKG)_TARGET_INSTALL_MARKER:=$($(PKG)_DEST_DIR)/.installed
$(PKG)_TARGET_BINARIES:= \
	$($(PKG)_DEST_DIR)/usr/bin/valgrind \
	$($(PKG)_DEST_DIR)/usr/bin/vgdb \
	$($(PKG)_DEST_DIR)/usr/bin/vgstack \
	$($(PKG)_DEST_DIR)/usr/bin/valgrind-listener \
	$($(PKG)_DEST_DIR)/usr/bin/valgrind-di-server
$(PKG)_PRUNE_BINARIES:= \
	$($(PKG)_DEST_DIR)/usr/bin/callgrind_annotate \
	$($(PKG)_DEST_DIR)/usr/bin/callgrind_control \
	$($(PKG)_DEST_DIR)/usr/bin/cg_annotate \
	$($(PKG)_DEST_DIR)/usr/bin/cg_diff \
	$($(PKG)_DEST_DIR)/usr/bin/cg_merge \
	$($(PKG)_DEST_DIR)/usr/bin/ms_print

$(PKG)_CONFIGURE_OPTIONS += --libexecdir=/usr/lib
$(PKG)_CONFIGURE_OPTIONS += --disable-docs


$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_TARGET_INSTALL_MARKER): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(VALGRIND_DIR)
	$(SUBMAKE) -C $(VALGRIND_DIR) DESTDIR="$(abspath $(VALGRIND_DEST_DIR))" install
	$(RM) -r $(VALGRIND_DEST_DIR)/usr/share/doc $(VALGRIND_DEST_DIR)/usr/share/info $(VALGRIND_DEST_DIR)/usr/share/man
	$(RM) $(VALGRIND_PRUNE_BINARIES)
	$(TARGET_STRIP) $(VALGRIND_TARGET_BINARIES) 2>/dev/null || true
	find "$(VALGRIND_DEST_DIR)/usr/lib/valgrind" -type f \( -name '*.so' -o -perm -0100 \) -exec $(TARGET_STRIP) {} + 2>/dev/null || true
	touch $@

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_INSTALL_MARKER)


$(pkg)-clean:
	-$(SUBMAKE) -C $(VALGRIND_DIR) clean

$(pkg)-uninstall:
	$(RM) -r \
		$(VALGRIND_DEST_DIR)/usr/bin/valgrind \
		$(VALGRIND_DEST_DIR)/usr/bin/vgdb \
		$(VALGRIND_DEST_DIR)/usr/bin/vgstack \
		$(VALGRIND_DEST_DIR)/usr/bin/valgrind-listener \
		$(VALGRIND_DEST_DIR)/usr/bin/valgrind-di-server \
		$(VALGRIND_DEST_DIR)/usr/lib/valgrind \
		$(VALGRIND_TARGET_INSTALL_MARKER)

$(PKG_FINISH)