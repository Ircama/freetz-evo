$(call PKG_INIT_BIN, 0.72.0)
$(PKG)_SOURCE_DOWNLOAD_NAME:=v$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=ca5ce083cec5187503ceb96d837c20d8efde85f03e62bba3a8890f8da526f2fc
$(PKG)_SITE:=https://github.com/junegunn/fzf/archive/refs/tags
$(PKG)_DIR:=$(SOURCE_DIR)/fzf-$($(PKG)_VERSION)
### WEBSITE:=https://github.com/junegunn/fzf
### MANPAGE:=https://github.com/junegunn/fzf#usage
### CHANGES:=https://github.com/junegunn/fzf/releases
### CVSREPO:=https://github.com/junegunn/fzf
### SUPPORT:=ircama
### STEWARD:=Ircama

$(PKG)_BINARY:=$($(PKG)_DIR)/fzf
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/fzf

$(PKG)_GO_VERSION := 1.25.10

$(PKG)_DEPENDS_ON += go-host

$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_ARCH_MIPS
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_ARCH_ARM
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_ARCH_X86
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_ARCH_AARCH64

$(PKG)_GO_OS := linux
$(PKG)_GO_ARCH := $(if $(FREETZ_TARGET_ARCH_MIPS),mips,$(if $(FREETZ_TARGET_ARCH_ARM),arm,$(if $(FREETZ_TARGET_ARCH_X86),386,$(if $(FREETZ_TARGET_ARCH_AARCH64),arm64,unknown))))
$(PKG)_GO_MIPS := $(if $(FREETZ_TARGET_ARCH_MIPS),softfloat,)
$(PKG)_GO_ARM := $(if $(FREETZ_TARGET_ARCH_ARM),$(if $(FREETZ_TARGET_ARCH_ARM_NEON),7,6),)

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	@echo "Building fzf with Go $(FZF_GO_VERSION)..."
	cd $(FZF_DIR); \
	export PATH=$(TOOLS_DIR)/go-host/bin:$$PATH; \
	GOOS=$(FZF_GO_OS) \
	GOARCH=$(FZF_GO_ARCH) \
	$(if $(FZF_GO_MIPS),GOMIPS=$(FZF_GO_MIPS),) \
	$(if $(FZF_GO_ARM),GOARM=$(FZF_GO_ARM),) \
	CGO_ENABLED=0 \
	go build \
		-v \
		-buildvcs=false \
		-trimpath \
		-ldflags="-s -w -X main.version=$(FZF_VERSION) -X main.revision=freetz" \
		-o fzf \
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