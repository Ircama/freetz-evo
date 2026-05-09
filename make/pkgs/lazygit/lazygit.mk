$(call PKG_INIT_BIN, 0.61.1)
$(PKG)_SOURCE_DOWNLOAD_NAME:=v$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=2a550c9b609c5eb0e1c2640e8114ac05b94c671803f77e08a9dcdbd66372e2c4
$(PKG)_SITE:=https://github.com/jesseduffield/lazygit/archive/refs/tags
$(PKG)_DIR:=$(SOURCE_DIR)/lazygit-$($(PKG)_VERSION)
### WEBSITE:=https://github.com/jesseduffield/lazygit
### MANPAGE:=https://github.com/jesseduffield/lazygit#usage
### CHANGES:=https://github.com/jesseduffield/lazygit/releases
### CVSREPO:=https://github.com/jesseduffield/lazygit
### SUPPORT:=ircama
### STEWARD:=Ircama

$(PKG)_BINARY:=$($(PKG)_DIR)/lazygit
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/lazygit

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
	@echo "Building lazygit with Go $(LAZYGIT_GO_VERSION)..."
	cd $(LAZYGIT_DIR); \
	export PATH=$(TOOLS_DIR)/go-host/bin:$$PATH; \
	GOOS=$(LAZYGIT_GO_OS) \
	GOARCH=$(LAZYGIT_GO_ARCH) \
	$(if $(LAZYGIT_GO_MIPS),GOMIPS=$(LAZYGIT_GO_MIPS),) \
	$(if $(LAZYGIT_GO_ARM),GOARM=$(LAZYGIT_GO_ARM),) \
	CGO_ENABLED=0 \
	go build \
		-v \
		-buildvcs=false \
		-mod=vendor \
		-trimpath \
		-ldflags="-s -w -X main.version=$(LAZYGIT_VERSION) -X main.commit=freetz -X main.buildSource=freetz" \
		-o lazygit \
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