$(call PKG_INIT_BIN, 1.3.1)
$(PKG)_SOURCE_DOWNLOAD_NAME:=v$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=396007bc0bc53de253391493bda1252757ba63af1a19db86cfb60a35cb9d290a
$(PKG)_SITE:=https://github.com/FiloSottile/age/archive/refs/tags
$(PKG)_DIR:=$(SOURCE_DIR)/age-$($(PKG)_VERSION)
### WEBSITE:=https://github.com/FiloSottile/age
### MANPAGE:=https://github.com/FiloSottile/age#usage
### CHANGES:=https://github.com/FiloSottile/age/releases
### CVSREPO:=https://github.com/FiloSottile/age
### SUPPORT:=ircama
### STEWARD:=Ircama

$(PKG)_BINARIES:=age age-keygen
$(PKG)_BINARIES_BUILD_DIR:=$($(PKG)_BINARIES:%=$($(PKG)_DIR)/%)
$(PKG)_BINARIES_TARGET_DIR:=$($(PKG)_BINARIES:%=$($(PKG)_DEST_DIR)/usr/bin/%)

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

$($(PKG)_BINARIES_BUILD_DIR): $($(PKG)_DIR)/%: $($(PKG)_DIR)/.configured
	@echo "Building $(@F) with Go $(AGE_GO_VERSION)..."
	cd $(AGE_DIR); \
	export PATH=$(TOOLS_DIR)/go-host/bin:$$PATH; \
	GOOS=$(AGE_GO_OS) \
	GOARCH=$(AGE_GO_ARCH) \
	$(if $(AGE_GO_MIPS),GOMIPS=$(AGE_GO_MIPS),) \
	$(if $(AGE_GO_ARM),GOARM=$(AGE_GO_ARM),) \
	CGO_ENABLED=0 \
	go build \
		-v \
		-buildvcs=false \
		-trimpath \
		-ldflags="-s -w -X main.Version=v$(AGE_VERSION)" \
		-o $(@F) \
		./cmd/$(@F)

$($(PKG)_BINARIES_TARGET_DIR): $($(PKG)_DEST_DIR)/usr/bin/%: $($(PKG)_DIR)/%
	$(INSTALL_BINARY_STRIP)

$(pkg):

$(pkg)-precompiled: $($(PKG)_BINARIES_TARGET_DIR)

$(pkg)-clean:
	-$(SUBMAKE) -C $(AGE_DIR) clean
	$(RM) $(AGE_BINARIES_BUILD_DIR) $(AGE_DIR)/.configured

$(pkg)-uninstall:
	$(RM) $(AGE_BINARIES_TARGET_DIR)

$(PKG_FINISH)