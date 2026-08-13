$(call PKG_INIT_BIN, 1.0)
$(PKG)_CATEGORY_PKGS:=Web interfaces

# HTML editors from GitHub (pinned)
# Note: avoid using $($(PKG)_...) in recipes/targets directly (PKG may change at execution time).
RTORRENT_CGI_EDITORS_VERSION:=1.2.2
RTORRENT_CGI_EDITORS_SOURCE:=rtorrent-rutorrent-editors-$(RTORRENT_CGI_EDITORS_VERSION).tar.gz
RTORRENT_CGI_EDITORS_HASH:=923fa4d44f1f4450ccdbfbd805514c24540078e3660365cf80c67b959fe279b6
RTORRENT_CGI_EDITORS_SITE:=https://github.com/Ircama/rtorrent-rutorrent-editors/archive/refs/tags
RTORRENT_CGI_EDITORS_DIR:=$(SOURCE_DIR)/rtorrent-rutorrent-editors-$(RTORRENT_CGI_EDITORS_VERSION)

# Intermediate variables to avoid double expansion in shell commands (pattern used by rutorrent.mk)
RTORRENT_CGI_PKG_DEST_DIR := $($(PKG)_DEST_DIR)

RTORRENT_CGI_EDITORS_TARGET_DIR:=$(RTORRENT_CGI_PKG_DEST_DIR)/usr/mww/rtorrent
RTORRENT_CGI_RTORRENT_EDITOR:=$(RTORRENT_CGI_EDITORS_DIR)/rtorrent_config_editor.html
RTORRENT_CGI_RUTORRENT_EDITOR:=$(RTORRENT_CGI_EDITORS_DIR)/rutorrent_config_editor.html
RTORRENT_CGI_RTORRENT_EDITOR_TARGET:=$(RTORRENT_CGI_EDITORS_TARGET_DIR)/rtorrent_config_editor.html
RTORRENT_CGI_RUTORRENT_EDITOR_TARGET:=$(RTORRENT_CGI_EDITORS_TARGET_DIR)/rutorrent_config_editor.html

$(PKG_UNPACKED)

# Download editor repository
$(DL_DIR)/$(RTORRENT_CGI_EDITORS_SOURCE): | $(DL_DIR)
	$(DL_TOOL) -o $(RTORRENT_CGI_EDITORS_SOURCE) $(DL_DIR) v$(RTORRENT_CGI_EDITORS_VERSION).tar.gz $(RTORRENT_CGI_EDITORS_SITE) $(RTORRENT_CGI_EDITORS_HASH)

# Unpack editors archive into source tree
$(RTORRENT_CGI_EDITORS_DIR)/.unpacked: $(DL_DIR)/$(RTORRENT_CGI_EDITORS_SOURCE)
	$(call UNPACK_TARBALL,$<,$(SOURCE_DIR))
	@touch $@

$(RTORRENT_CGI_RTORRENT_EDITOR) $(RTORRENT_CGI_RUTORRENT_EDITOR): $(RTORRENT_CGI_EDITORS_DIR)/.unpacked

# Install editor HTML files into package root
$(RTORRENT_CGI_RTORRENT_EDITOR_TARGET): $(RTORRENT_CGI_RTORRENT_EDITOR)
	mkdir -p $(dir $@)
	$(INSTALL_FILE)

$(RTORRENT_CGI_RUTORRENT_EDITOR_TARGET): $(RTORRENT_CGI_RUTORRENT_EDITOR)
	mkdir -p $(dir $@)
	$(INSTALL_FILE)

$(RTORRENT_CGI_EDITORS_TARGET_DIR)/.installed: $(RTORRENT_CGI_RTORRENT_EDITOR_TARGET) $(RTORRENT_CGI_RUTORRENT_EDITOR_TARGET)
	@touch $@

$(pkg):

$(pkg)-precompiled: $(RTORRENT_CGI_EDITORS_TARGET_DIR)/.installed

$(pkg)-clean:
	$(RM) $(RTORRENT_CGI_EDITORS_TARGET_DIR)/.installed

$(PKG_FINISH)
