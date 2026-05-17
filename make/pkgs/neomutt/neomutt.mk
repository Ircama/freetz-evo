$(call PKG_INIT_BIN, 20260504)
$(PKG)_SOURCE_DOWNLOAD_NAME:=$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=93fd8344c12cd857f084f8d7cc1187479f79036ab9725cfdbc81c0cc845f1615
$(PKG)_SITE:=https://github.com/neomutt/neomutt/archive/refs/tags
$(PKG)_DIR:=$(SOURCE_DIR)/neomutt-$($(PKG)_VERSION)
### WEBSITE:=https://neomutt.org/
### MANPAGE:=https://neomutt.org/guide/
### CHANGES:=https://github.com/neomutt/neomutt/releases
### CVSREPO:=https://github.com/neomutt/neomutt
### STEWARD:=Ircama

$(PKG)_BINARY:=$($(PKG)_DIR)/neomutt
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/neomutt

$(PKG)_DEPENDS_ON += ncursesw openssl
$(PKG)_DEPENDS_ON += zlib $(if $(FREETZ_OPENSSL_VERSION_30_MIN),libatomic)

ifeq ($(strip $(FREETZ_TARGET_UCLIBC_0_9_28)),y)
$(PKG)_DEPENDS_ON += iconv
$(PKG)_CONFIGURE_ENV += LIBS="-liconv"
endif

$(PKG)_REBUILD_SUBOPTS += FREETZ_OPENSSL_SHORT_VERSION

$(PKG)_CONFIGURE_PRE_CMDS += $(call PKG_PREVENT_RPATH_HARDCODING,./configure)

$(PKG)_CONFIGURE_OPTIONS += --disable-doc
$(PKG)_CONFIGURE_OPTIONS += --disable-nls
$(PKG)_CONFIGURE_OPTIONS += --disable-idn2
$(PKG)_CONFIGURE_OPTIONS += --disable-gpgme
$(PKG)_CONFIGURE_OPTIONS += --disable-gnutls
$(PKG)_CONFIGURE_OPTIONS += --disable-gsasl
$(PKG)_CONFIGURE_OPTIONS += --disable-sasl
$(PKG)_CONFIGURE_OPTIONS += --disable-lua
$(PKG)_CONFIGURE_OPTIONS += --disable-notmuch
$(PKG)_CONFIGURE_OPTIONS += --disable-sqlite
$(PKG)_CONFIGURE_OPTIONS += --disable-tokyocabinet
$(PKG)_CONFIGURE_OPTIONS += --disable-lmdb
$(PKG)_CONFIGURE_OPTIONS += --locales-fix
$(PKG)_CONFIGURE_OPTIONS += --ssl
$(PKG)_CONFIGURE_OPTIONS += --with-ncurses="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr"
$(PKG)_CONFIGURE_OPTIONS += --with-ssl="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr"

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)

$($(PKG)_DIR)/.configured: $($(PKG)_DIR)/.unpacked
	(cd $(NEOMUTT_DIR) && \
		$(TARGET_CONFIGURE_PRE_CMDS) \
		$(NEOMUTT_CONFIGURE_PRE_CMDS) \
		$(TARGET_CONFIGURE_ENV) \
		$(NEOMUTT_CONFIGURE_ENV) \
		GLOBAL_LIBDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib" \
		CONFIG_SITE="$(TARGET_SITE)" \
		./configure \
			--host=$(GNU_TARGET_NAME) \
			--build=$(GNU_HOST_NAME) \
			--prefix=/usr \
			$(NEOMUTT_CONFIGURE_OPTIONS) \
	) $(SILENT)
	touch $@

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(NEOMUTT_DIR)

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	$(INSTALL_BINARY_STRIP)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(NEOMUTT_DIR) clean

$(pkg)-uninstall:
	$(RM) $(NEOMUTT_TARGET_BINARY)

$(PKG_FINISH)