$(call PKG_INIT_BIN, 2.1.2)
$(PKG)_SOURCE_DOWNLOAD_NAME:=v$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=1b933139da1d08647bf5b3f112cab9548fdc2b40c056c7fa3d84d8706de5265a
$(PKG)_SITE:=https://github.com/charmbracelet/glow/archive/refs/tags
$(PKG)_DIR:=$(SOURCE_DIR)/glow-$($(PKG)_VERSION)
### WEBSITE:=https://github.com/charmbracelet/glow
### MANPAGE:=https://github.com/charmbracelet/glow#usage
### CHANGES:=https://github.com/charmbracelet/glow/releases
### CVSREPO:=https://github.com/charmbracelet/glow
### SUPPORT:=ircama
### STEWARD:=Ircama

$(PKG)_BINARY:=$($(PKG)_DIR)/glow
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/glow

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
	@echo "Building glow with Go $(GLOW_GO_VERSION)..."
	cd $(GLOW_DIR); \
	export PATH=$(TOOLS_DIR)/go-host/bin:$$PATH; \
	GOOS=$(GLOW_GO_OS) \
	GOARCH=$(GLOW_GO_ARCH) \
	$(if $(GLOW_GO_MIPS),GOMIPS=$(GLOW_GO_MIPS),) \
	$(if $(GLOW_GO_ARM),GOARM=$(GLOW_GO_ARM),) \
	CGO_ENABLED=0 \
	go build \
		-v \
		-buildvcs=false \
		-trimpath \
		-ldflags="-s -w -X main.Version=$(GLOW_VERSION) -X main.CommitSHA=freetz" \
		-o glow \
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