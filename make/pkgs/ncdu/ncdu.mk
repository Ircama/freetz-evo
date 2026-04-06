$(call PKG_INIT_BIN, 1.19)
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=30363019180cde0752c7fb006c12e154920412f4e1b5dc3090654698496bb17d
$(PKG)_SITE:=https://dev.yorhel.nl/download
### WEBSITE:=https://dev.yorhel.nl/ncdu
### MANPAGE:=https://linux.die.net/man/1/ncdu
### CHANGES:=https://dev.yorhel.nl/ncdu/changes
### CVSREPO:=https://code.blicky.net/yorhel/ncdu

$(PKG)_BINARY:=$($(PKG)_DIR)/ncdu
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/ncdu

$(PKG)_DEPENDS_ON += ncurses

$(PKG)_CONFIGURE_OPTIONS += --without-ncursesw

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(NCDU_DIR)

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	$(INSTALL_BINARY_STRIP)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	-$(SUBMAKE) -C $(NCDU_DIR) clean
	$(RM) $(NCDU_DIR)/.configured

$(pkg)-uninstall:
	$(RM) $(NCDU_TARGET_BINARY)

$(PKG_FINISH)
