$(call PKG_INIT_BIN, 1.78.0)
$(PKG)_SOURCE:=grpcio-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=grpcio-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/g/grpcio
$(PKG)_HASH:=7382b95189546f375c174f53a5fa873cef91c4b8005faa05cc5b3beea9c4f1c5
### WEBSITE:=https://grpc.io/
### CHANGES:=https://github.com/grpc/grpc/releases
### CVSREPO:=https://github.com/grpc/grpc
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/grpc/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_GRPCIO, , \
		GRPC_BUILD_WITH_BORING_SSL_ASM=0 \
		GRPC_PYTHON_BUILD_SYSTEM_OPENSSL=1 \
		GRPC_PYTHON_BUILD_EXT_COMPILER_JOBS=1 \
		CPATH="$(PYTHON3_STAGING_INC_DIR)" \
		CPPFLAGS="$(TARGET_CPPFLAGS) -I$(PYTHON3_STAGING_INC_DIR)" \
		CFLAGS="$(TARGET_CFLAGS) -I$(PYTHON3_STAGING_INC_DIR)" \
		CXXFLAGS="$(TARGET_CXXFLAGS) -I$(PYTHON3_STAGING_INC_DIR)" \
		LDFLAGS="$(TARGET_LDFLAGS) -L$(PYTHON3_STAGING_LIB_DIR)" \
	)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_GRPCIO_DIR)/.configured
	$(RM) -r $(PYTHON3_GRPCIO_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_GRPCIO_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/grpc \
		$(PYTHON3_GRPCIO_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/grpcio-*.dist-info

$(PKG_FINISH)
