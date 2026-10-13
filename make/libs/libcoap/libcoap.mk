$(call PKG_INIT_LIB, 4.3.5b)
$(PKG)_LIB_VERSION:=3.2.2
$(PKG)_SOURCE:=libcoap-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=v$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=383a17d8466cee7c1cb1d4dfbffad2651004850b29eb590e9591c7bedd46741d
$(PKG)_SITE:=https://github.com/obgm/libcoap/archive/refs/tags
### WEBSITE:=https://libcoap.net/
### CHANGES:=https://github.com/obgm/libcoap/blob/develop/ChangeLog
### CVSREPO:=https://github.com/obgm/libcoap

$(PKG)_CATEGORY_LIBS:=Local Network

# The GitHub archive unpacks to libcoap-<version>/, while freetz expects the
# sources directly in $(PKG)_DIR.
$(PKG)_TARBALL_STRIP_COMPONENTS := 1

$(PKG)_BINARY:=$($(PKG)_DIR)/src/.libs/libcoap-3-openssl.so.$($(PKG)_LIB_VERSION)
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libcoap-3-openssl.so.$($(PKG)_LIB_VERSION)
$(PKG)_TARGET_BINARY:=$($(PKG)_TARGET_DIR)/libcoap-3-openssl.so.$($(PKG)_LIB_VERSION)

# The GitHub tag archive ships no generated build system, so the autotools files
# have to be regenerated before configure can run.
$(PKG)_CONFIGURE_PRE_CMDS += ./autogen.sh;
$(PKG)_CONFIGURE_PRE_CMDS += $(call PKG_PREVENT_RPATH_HARDCODING,./configure)

$(PKG)_CONFIGURE_OPTIONS += --with-openssl
$(PKG)_CONFIGURE_OPTIONS += --disable-documentation
$(PKG)_CONFIGURE_OPTIONS += --disable-doxygen
$(PKG)_CONFIGURE_OPTIONS += --disable-manpages
$(PKG)_CONFIGURE_OPTIONS += --disable-tests
$(PKG)_CONFIGURE_OPTIONS += --enable-examples
$(PKG)_CONFIGURE_OPTIONS += --disable-oscore
$(PKG)_CONFIGURE_OPTIONS += --disable-largefile

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(LIBCOAP_DIR) all

$($(PKG)_STAGING_BINARY): $($(PKG)_BINARY)
	$(SUBMAKE) -C $(LIBCOAP_DIR) \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install

$($(PKG)_TARGET_BINARY): $($(PKG)_STAGING_BINARY)
	$(INSTALL_LIBRARY_STRIP)
# The command line client and server are useful on the box (the library alone is
# only useful to programs): install the DTLS variants and a plain alias for the
# client. Note that the `coapcmd` helper that tradfricoap expects is a *different*
# program, written in Go, and is not the client of libcoap.
	mkdir -p $(patsubst %/lib/freetz,%/bin,$(LIBCOAP_TARGET_DIR))
	for d in $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin $(TARGET_TOOLCHAIN_STAGING_DIR)/bin; do \
		for f in coap-client-openssl coap-server-openssl coap-rd-openssl; do \
			if [ -e $$d/$$f ]; then \
				cp -f $$d/$$f $(patsubst %/lib/freetz,%/bin,$(LIBCOAP_TARGET_DIR))/$$f && \
				chmod 755 $(patsubst %/lib/freetz,%/bin,$(LIBCOAP_TARGET_DIR))/$$f; \
			fi; \
		done; \
	done
	ln -sf coap-client-openssl $(patsubst %/lib/freetz,%/bin,$(LIBCOAP_TARGET_DIR))/coap-client

$(pkg): $($(PKG)_STAGING_BINARY)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	$(RM) -r \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libcoap-3* \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/coap3 \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/libcoap-3*.pc \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin/coap-client* \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin/coap-server* \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin/coap-rd* \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin/coapcmd*

$(pkg)-uninstall:
	$(RM) $(LIBCOAP_TARGET_DIR)/libcoap-3*.so*

$(PKG_FINISH)
