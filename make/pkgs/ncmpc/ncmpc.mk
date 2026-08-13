$(call PKG_INIT_BIN, 0.52)
# ncmpc 0.52 depends on fmt >= 9 (dependency('fmt', version: '>= 9') in
# src/lib/fmt/meson.build). freetz's libfmt 12.2.0 is gated on uClibc
# >= 1.0.58 (it needs a recent toolchain), so ncmpc must also be gated on
# FREETZ_TARGET_UCLIBC_1_0_58_MIN in Config.in (select FREETZ_LIB_libfmt)
# and declare the DEPENDS_ON below. Without fmt the meson sanity check fails
# with "cc1plus: fatal error: fmt/format.h: No such file or directory".
$(PKG)_SOURCE_DOWNLOAD_NAME:=v$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=4240965253789479bd048c9b691c710418012edaec5d0000283a95dfcb55f1a5
$(PKG)_SITE:=https://github.com/MusicPlayerDaemon/ncmpc/archive/refs/tags
### WEBSITE:=https://www.musicpd.org/clients/ncmpc/
### CHANGES:=https://github.com/MusicPlayerDaemon/ncmpc/releases
### CVSREPO:=https://github.com/MusicPlayerDaemon/ncmpc

$(PKG)_CATEGORY_PKGS:=Audio

$(PKG)_BINARY:=$($(PKG)_DIR)/builddir/ncmpc
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/ncmpc

$(PKG)_DEPENDS_ON += meson-host
$(PKG)_DEPENDS_ON += libmpdclient
$(PKG)_DEPENDS_ON += ncursesw
$(PKG)_DEPENDS_ON += libfmt

$(PKG)_DEPENDS_ON += $(if $(FREETZ_PACKAGE_NCMPC_WITH_ICONV),iconv)
$(PKG)_DEPENDS_ON += $(if $(FREETZ_PACKAGE_NCMPC_WITH_REGEX),pcre2)
$(PKG)_DEPENDS_ON += $(if $(FREETZ_PACKAGE_NCMPC_WITH_NLS),gettext)
$(PKG)_DEPENDS_ON += $(if $(FREETZ_PACKAGE_NCMPC_WITH_LIRC),lirc)

$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_MESON_FAMILY
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_NCMPC_WITH_ICONV
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_NCMPC_WITH_LIRC
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_NCMPC_WITH_NLS
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_NCMPC_WITH_REGEX

# Force include <fmt/format.h> for all translation units (fmt 12 moved format
# functions out of <fmt/core.h>; ncmpc 0.52 uses <fmt/core.h> in many files)
$(PKG)_CONFIGURE_OPTIONS += -Dcpp_args=-include\ fmt/format.h

$(PKG)_CONFIGURE_OPTIONS += -D documentation=disabled
$(PKG)_CONFIGURE_OPTIONS += -D lirc=$(if $(FREETZ_PACKAGE_NCMPC_WITH_LIRC),enabled,disabled)
$(PKG)_CONFIGURE_OPTIONS += -D regex=$(if $(FREETZ_PACKAGE_NCMPC_WITH_REGEX),enabled,disabled)
$(PKG)_CONFIGURE_OPTIONS += -D nls=$(if $(FREETZ_PACKAGE_NCMPC_WITH_NLS),enabled,disabled)
$(PKG)_CONFIGURE_OPTIONS += -D iconv=$(if $(FREETZ_PACKAGE_NCMPC_WITH_ICONV),enabled,disabled)
$(PKG)_CONFIGURE_OPTIONS += -D locale=enabled
$(PKG)_CONFIGURE_OPTIONS += -D multibyte=true
$(PKG)_CONFIGURE_OPTIONS += -D colors=true
$(PKG)_CONFIGURE_OPTIONS += -D mouse=enabled
$(PKG)_CONFIGURE_OPTIONS += -D help_screen=true
$(PKG)_CONFIGURE_OPTIONS += -D library_screen=true
$(PKG)_CONFIGURE_OPTIONS += -D search_screen=true
$(PKG)_CONFIGURE_OPTIONS += -D song_screen=true
$(PKG)_CONFIGURE_OPTIONS += -D key_screen=true
$(PKG)_CONFIGURE_OPTIONS += -D outputs_screen=true
$(PKG)_CONFIGURE_OPTIONS += -D lyrics_screen=true
$(PKG)_CONFIGURE_OPTIONS += -D manual=false
$(PKG)_CONFIGURE_OPTIONS += -D html_manual=false

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_MESON)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBNINJA) -C $(NCMPC_DIR)/builddir/

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	$(INSTALL_BINARY_STRIP)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBNINJA) -C $(NCMPC_DIR)/builddir/ clean

$(pkg)-uninstall:
	$(RM) $(NCMPC_TARGET_BINARY)

$(PKG_FINISH)
