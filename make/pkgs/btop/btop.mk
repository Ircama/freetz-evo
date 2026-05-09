$(call PKG_INIT_BIN, 1.4.7)
$(PKG)_SOURCE_DOWNLOAD_NAME:=v$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=933de2e4d1b2211a638be463eb6e8616891bfba73aef5d38060bd8319baeefc6
$(PKG)_SITE:=https://github.com/aristocratos/btop/archive/refs/tags
### WEBSITE:=https://github.com/aristocratos/btop
### MANPAGE:=https://github.com/aristocratos/btop#readme
### CHANGES:=https://github.com/aristocratos/btop/releases
### CVSREPO:=https://github.com/aristocratos/btop

$(PKG)_BINARY:=$($(PKG)_DIR)/bin/btop
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/btop
$(PKG)_THEMES_SOURCE_DIR:=$($(PKG)_DIR)/themes
$(PKG)_THEMES_TARGET_DIR:=$($(PKG)_DEST_DIR)/usr/share/btop/themes

$(PKG)_DEPENDS_ON += $(STDCXXLIB)

$(PKG)_PATCH_POST_CMDS += perl -0pi -e 's/\x23include <clocale>\n/\x23include <clocale>\n\x23include <cstdlib>\n/; s/quick_exit\(excode\);/_Exit(excode);/' src/btop.cpp;

$(PKG)_REBUILD_SUBOPTS += FREETZ_STDCXXLIB
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_BTOP_THEMES


$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(BTOP_DIR) btop \
		CC="$(TARGET_CC)" \
		CXX="$(TARGET_CXX)" \
		AR="$(TARGET_AR)" \
		RANLIB="$(TARGET_RANLIB)" \
		CXXFLAGS="$(TARGET_CFLAGS)" \
		LDFLAGS="$(TARGET_LDFLAGS)" \
		GPU_SUPPORT=false \
		QUIET=true

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	$(INSTALL_BINARY_STRIP)

$($(PKG)_THEMES_TARGET_DIR): $($(PKG)_DIR)/.configured
	$(RM) -r $(BTOP_THEMES_TARGET_DIR)
	mkdir -p $(dir $(BTOP_THEMES_TARGET_DIR))
	cp -a $(BTOP_THEMES_SOURCE_DIR) $(dir $(BTOP_THEMES_TARGET_DIR))

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)
$(pkg)-precompiled: $(if $(FREETZ_PACKAGE_BTOP_THEMES),$($(PKG)_THEMES_TARGET_DIR))


$(pkg)-clean:
	-$(SUBMAKE) -C $(BTOP_DIR) clean

$(pkg)-uninstall:
	$(RM) $(BTOP_TARGET_BINARY)
	$(RM) -r $(BTOP_THEMES_TARGET_DIR)

$(PKG_FINISH)