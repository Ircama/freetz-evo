$(call PKG_INIT_BIN, 4.53.2)
$(PKG)_SOURCE_DOWNLOAD_NAME:=v$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=1bc19bb8b1029148afa3465a9383f6dcccb1ecce28a0af1d81f07c93396ce37d
$(PKG)_SITE:=https://github.com/mikefarah/yq/archive/refs/tags
$(PKG)_DIR:=$(SOURCE_DIR)/yq-$($(PKG)_VERSION)
### WEBSITE:=https://github.com/mikefarah/yq
### MANPAGE:=https://mikefarah.gitbook.io/yq/
### CHANGES:=https://github.com/mikefarah/yq/releases
### CVSREPO:=https://github.com/mikefarah/yq
### SUPPORT:=ircama
### STEWARD:=Ircama

$(PKG)_BINARY:=$($(PKG)_DIR)/yq
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/yq

$(PKG)_GO_VERSION := 1.25.10

$(PKG)_DEPENDS_ON += go-host

$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_ARCH_MIPS
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_ARCH_ARM
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_ARCH_X86
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_ARCH_AARCH64

$(PKG)_GO_OS := linux
$(PKG)_GO_ARCH := $(FREETZ_TARGET_GO_ARCH)
$(PKG)_GO_MIPS := $(FREETZ_TARGET_GO_MIPS)
$(PKG)_GO_ARM := $(FREETZ_TARGET_GO_ARM)

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	@echo "Building yq with Go $(YQ_GO_VERSION)..."
	cd $(YQ_DIR); \
	export PATH=$(TOOLS_DIR)/go-host/bin:$$PATH; \
	GOOS=$(YQ_GO_OS) \
	GOARCH=$(YQ_GO_ARCH) \
	$(if $(YQ_GO_MIPS),GOMIPS=$(YQ_GO_MIPS),) \
	$(if $(YQ_GO_ARM),GOARM=$(YQ_GO_ARM),) \
	CGO_ENABLED=0 \
	go build \
		-v \
		-buildvcs=false \
		-trimpath \
		-ldflags="-s -w" \
		-o yq \
		.

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	$(INSTALL_BINARY_STRIP)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $($(PKG)_DIR) clean
	$(RM) $($(PKG)_BINARY) $($(PKG)_DIR)/.configured

$(pkg)-uninstall:
	$(RM) $($(PKG)_TARGET_BINARY)

$(PKG_FINISH)