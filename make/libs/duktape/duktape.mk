$(call PKG_INIT_LIB, 2.6.0)
$(PKG)_LIB_VERSION:=206.20600
$(PKG)_SOURCE:=duktape-$($(PKG)_VERSION).tar.xz
$(PKG)_HASH:=96f4a05a6c84590e53b18c59bb776aaba80a205afbbd92b82be609ba7fe75fa7
$(PKG)_SITE:=https://github.com/svaarala/duktape/releases/download/v$($(PKG)_VERSION)
### WEBSITE:=https://duktape.org/
### CHANGES:=https://github.com/svaarala/duktape/releases
### CVSREPO:=https://github.com/svaarala/duktape

$(PKG)_BINARY:=$($(PKG)_DIR)/libduktape.so.$($(PKG)_LIB_VERSION)
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libduktape.so.$($(PKG)_LIB_VERSION)
$(PKG)_TARGET_BINARY:=$($(PKG)_TARGET_DIR)/libduktape.so.$($(PKG)_LIB_VERSION)

# Duktape is a simple C library with a hand-written Makefile (Makefile.sharedlibrary)
# It uses DUK_VERSION (e.g. 20600 for 2.6.0) and SONAME_VERSION (e.g. 206)
# The REAL_VERSION = SONAME_VERSION.DUK_VERSION = 206.20600, producing libduktape.so.206.20600
# We override DUKTAPE_SRCDIR to point to the src/ subdirectory

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)

$($(PKG)_DIR)/.configured: $($(PKG)_DIR)/.unpacked
	@touch $@

# Build the shared library directly using the cross-compiler
$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	cd $(DUKTAPE_DIR) && \
		$(TARGET_CC) -shared -fPIC $(TARGET_CFLAGS) -Wall -Wextra -Os \
		-Wl,-soname,libduktape.so.206 \
		-o libduktape.so.206.20600 \
		src/duktape.c -lm

# Install to staging
$($(PKG)_STAGING_BINARY): $($(PKG)_BINARY)
	mkdir -p $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib
	cp $(DUKTAPE_DIR)/libduktape.so.206.20600 $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/
	cd $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib && \
		ln -sf libduktape.so.206.20600 libduktape.so.206 && \
		ln -sf libduktape.so.206 libduktape.so
	mkdir -p $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include
	cp $(DUKTAPE_DIR)/src/duktape.h $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/
	cp $(DUKTAPE_DIR)/src/duk_config.h $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/
	@touch $@

$($(PKG)_TARGET_BINARY): $($(PKG)_STAGING_BINARY)
	$(INSTALL_LIBRARY_STRIP)

$(pkg): $($(PKG)_STAGING_BINARY)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	$(RM) -f $(DUKTAPE_DIR)/libduktape.so*
	$(RM) -r \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/duktape.h \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/duk_config.h \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libduktape*

$(pkg)-uninstall:
	$(RM) $(DUKTAPE_TARGET_DIR)/libduktape*.so*

$(PKG_FINISH)
