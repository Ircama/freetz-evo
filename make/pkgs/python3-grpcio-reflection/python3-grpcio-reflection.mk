$(call PKG_INIT_BIN, 1.78.1)
$(PKG)_SOURCE:=grpcio-reflection-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=grpcio_reflection-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/g/grpcio-reflection
$(PKG)_HASH:=224c0d604207954923fd6f8dbec541e0976a64ab1be65d2ee40844ce16c762ab
### WEBSITE:=https://grpc.io/
### CVSREPO:=https://github.com/grpc/grpc

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-grpcio

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/grpc_reflection/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_GRPCIO_REFLECTION, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_GRPCIO_REFLECTION_DIR)/.configured
	$(RM) -r $(PYTHON3_GRPCIO_REFLECTION_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_GRPCIO_REFLECTION_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/grpc_reflection \
		$(PYTHON3_GRPCIO_REFLECTION_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/grpcio_reflection-*.dist-info

$(PKG_FINISH)
