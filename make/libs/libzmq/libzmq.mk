$(call PKG_INIT_LIB, 4.3.5)
$(PKG)_LIB_VERSION:=5.2.5
$(PKG)_SOURCE_DOWNLOAD_NAME:=zeromq-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=6653ef5910f17954861fe72332e68b03ca6e4d9c7160eb3a8de5a5a913bfab43
$(PKG)_SITE:=https://github.com/zeromq/libzmq/releases/download/v$($(PKG)_VERSION)
### WEBSITE:=https://zeromq.org/
### CHANGES:=https://github.com/zeromq/libzmq/releases
### CVSREPO:=https://github.com/zeromq/libzmq

$(PKG)_BINARY:=$($(PKG)_DIR)/src/.libs/libzmq.so.$($(PKG)_LIB_VERSION)
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libzmq.so.$($(PKG)_LIB_VERSION)
$(PKG)_TARGET_BINARY:=$($(PKG)_TARGET_DIR)/libzmq.so.$($(PKG)_LIB_VERSION)

$(PKG)_CONFIGURE_PRE_CMDS += $(call PKG_PREVENT_RPATH_HARDCODING,./configure)
$(PKG)_CONFIGURE_OPTIONS += --enable-shared
$(PKG)_CONFIGURE_OPTIONS += --enable-static
$(PKG)_CONFIGURE_OPTIONS += --disable-curve
$(PKG)_CONFIGURE_OPTIONS += --disable-curve-keygen
$(PKG)_CONFIGURE_OPTIONS += --disable-drafts
$(PKG)_CONFIGURE_OPTIONS += --enable-libunwind=no
$(PKG)_CONFIGURE_OPTIONS += --with-libsodium=no
$(PKG)_CONFIGURE_OPTIONS += --with-norm=no
$(PKG)_CONFIGURE_OPTIONS += --with-pgm=no
$(PKG)_CONFIGURE_OPTIONS += --with-vmci=no


$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(LIBZMQ_DIR)

$($(PKG)_STAGING_BINARY): $($(PKG)_BINARY)
	$(SUBMAKE) -C $(LIBZMQ_DIR) \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install
	$(PKG_FIX_LIBTOOL_LA) \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libzmq.la \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/libzmq.pc

$($(PKG)_TARGET_BINARY): $($(PKG)_STAGING_BINARY)
	$(INSTALL_LIBRARY_STRIP_WILDCARD_BEFORE_SO)

# Ensure libzmq.pc exists even if staging binary is up-to-date
$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/libzmq.pc:
	@mkdir -p $(dir $@)
	echo -ne \
		"prefix=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr\n"\
		"exec_prefix=\$${prefix}\n"\
		"libdir=\$${prefix}/lib\n"\
		"includedir=\$${prefix}/include\n"\
		"\n"\
		"Name: libzmq\n"\
		"Description: ZeroMQ library\n"\
		"Version: $(LIBZMQ_VERSION)\n"\
		"Requires:\n"\
		"Libs: -L\$${libdir} -lzmq\n"\
		"Cflags: -I\$${includedir}\n"\
		>$@

$(pkg): $($(PKG)_STAGING_BINARY) $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/libzmq.pc

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	-$(SUBMAKE) -C $(LIBZMQ_DIR) clean
	$(RM) -r \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libzmq* \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/libzmq.pc \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/zmq.h \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/zmq_utils.h

$(pkg)-uninstall:
	$(RM) $(LIBZMQ_TARGET_DIR)/libzmq.so*

$(PKG_FINISH)