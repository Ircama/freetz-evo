$(call PKG_INIT_BIN, 0.17.0)
$(PKG)_SOURCE_DOWNLOAD_NAME:=v$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=763a7f89dfebf8e77f86e680bace48a09423cfb9e4b4f4ba22d2c9836d311f95
$(PKG)_SITE:=https://github.com/charmbracelet/gum/archive/refs/tags
$(PKG)_DIR:=$(SOURCE_DIR)/gum-$($(PKG)_VERSION)
### WEBSITE:=https://github.com/charmbracelet/gum
### MANPAGE:=https://github.com/charmbracelet/gum#readme
### CHANGES:=https://github.com/charmbracelet/gum/releases
### CVSREPO:=https://github.com/charmbracelet/gum
### SUPPORT:=ircama
### STEWARD:=Ircama

$(PKG)_BINARY:=$($(PKG)_DIR)/gum
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/gum

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
	@echo "Building gum with Go $(GUM_GO_VERSION)..."
	cd $(GUM_DIR); \
	export PATH=$(TOOLS_DIR)/go-host/bin:$$PATH; \
	GOOS=$(GUM_GO_OS) \
	GOARCH=$(GUM_GO_ARCH) \
	$(if $(GUM_GO_MIPS),GOMIPS=$(GUM_GO_MIPS),) \
	$(if $(GUM_GO_ARM),GOARM=$(GUM_GO_ARM),) \
	CGO_ENABLED=0 \
	go build \
		-v \
		-buildvcs=false \
		-trimpath \
		-ldflags="-s -w -X main.Version=$(GUM_VERSION) -X main.CommitSHA=freetz" \
		-o gum \
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