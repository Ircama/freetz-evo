$(call TOOLS_INIT, 3.21.12)
$(PKG)_SOURCE:=protobuf-cpp-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=4eab9b524aa5913c6fffb20b2a8abf5ef7f95a80bc0701f3a6dbb4c607f73460
$(PKG)_SITE:=https://github.com/protocolbuffers/protobuf/releases/download/v$(patsubst 3.%,%,$($(PKG)_VERSION))
### WEBSITE:=https://protobuf.dev/
### CHANGES:=https://github.com/protocolbuffers/protobuf/releases
### CVSREPO:=https://github.com/protocolbuffers/protobuf

$(PKG)_DEPENDS_ON+=cmake-host
$(PKG)_BUILD_DIR:=$($(PKG)_DIR)/builddir
$(PKG)_INSTALL_DIR:=$(abspath $(HOST_TOOLS_DIR))/protobuf
$(PKG)_BINARY:=$($(PKG)_BUILD_DIR)/protoc
$(PKG)_TARGET_BINARY:=$($(PKG)_INSTALL_DIR)/bin/protoc

$(TOOLS_SOURCE_DOWNLOAD)
$(TOOLS_UNPACKED)

$($(PKG)_DIR)/.configured: $($(PKG)_DIR)/.unpacked
	$(TOOLS_SUBCMAKE) \
		-B $(PROTOBUF_HOST_BUILD_DIR) \
		-S $(PROTOBUF_HOST_DIR)/cmake \
		-DCMAKE_BUILD_TYPE=Release \
		-DCMAKE_INSTALL_PREFIX=$(PROTOBUF_HOST_INSTALL_DIR) \
		-DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
		-Dprotobuf_BUILD_TESTS=OFF \
		-Dprotobuf_BUILD_SHARED_LIBS=OFF \
		-Dprotobuf_WITH_ZLIB=OFF \
		-Dprotobuf_BUILD_PROTOC_BINARIES=ON
	@touch $@

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(TOOLS_SUBCMAKE) --build $(PROTOBUF_HOST_BUILD_DIR)

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	$(TOOLS_SUBCMAKE) --install $(PROTOBUF_HOST_BUILD_DIR)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(CMAKE) --build $(PROTOBUF_HOST_BUILD_DIR) --target clean
	$(RM) $(PROTOBUF_HOST_DIR)/.configured

$(pkg)-dirclean:
	$(RM) -r $(PROTOBUF_HOST_DIR)

$(pkg)-distclean: $(pkg)-dirclean
	$(RM) -r $(PROTOBUF_HOST_INSTALL_DIR)

$(TOOLS_FINISH)
