$(call PKG_INIT_BIN, 1.78.1)
$(PKG)_SOURCE:=grpcio-status-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=grpcio_status-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/g/grpcio-status
$(PKG)_HASH:=47e7fa903549c5881344f1cba23c814b5f69d09233541036eb25642d32497c8e
### WEBSITE:=https://grpc.io/
### CVSREPO:=https://github.com/grpc/grpc
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-grpcio

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/grpc_status/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_GRPCIO_STATUS, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_GRPCIO_STATUS_DIR)/.configured
	$(RM) -r $(PYTHON3_GRPCIO_STATUS_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_GRPCIO_STATUS_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/grpc_status \
		$(PYTHON3_GRPCIO_STATUS_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/grpcio_status-*.dist-info

$(PKG_FINISH)
