$(call PKG_INIT_BIN, 0.18.1)
$(PKG)_SOURCE_DOWNLOAD_NAME:=v$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=4b8e2b6cb20e9707e14b9b9d92ddb6f2e913523754e1f123e2e6f3321e67f7ca
$(PKG)_SITE:=https://github.com/restic/restic/archive/refs/tags
$(PKG)_DIR:=$(SOURCE_DIR)/restic-$($(PKG)_VERSION)
### WEBSITE:=https://github.com/restic/restic
### MANPAGE:=https://restic.readthedocs.io/en/stable/
### CHANGES:=https://github.com/restic/restic/releases
### CVSREPO:=https://github.com/restic/restic
### SUPPORT:=ircama
### STEWARD:=Ircama

$(PKG)_BINARY:=$($(PKG)_DIR)/restic
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/restic

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
$(PKG)_GO_TAGS := disable_grpc_modules

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	@echo "Building restic with Go $(RESTIC_GO_VERSION)..."
	cd $(RESTIC_DIR); \
	export PATH=$(TOOLS_DIR)/go-host/bin:$$PATH; \
	GOOS=$(RESTIC_GO_OS) \
	GOARCH=$(RESTIC_GO_ARCH) \
	$(if $(RESTIC_GO_MIPS),GOMIPS=$(RESTIC_GO_MIPS),) \
	$(if $(RESTIC_GO_ARM),GOARM=$(RESTIC_GO_ARM),) \
	CGO_ENABLED=0 \
	go build \
		-v \
		-buildvcs=false \
		-trimpath \
		-tags "$(RESTIC_GO_TAGS)" \
		-ldflags="-s -w -X main.version=$(RESTIC_VERSION)" \
		-o restic \
		./cmd/restic

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	$(INSTALL_BINARY_STRIP)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(RESTIC_DIR) clean
	$(RM) $(RESTIC_BINARY) $(RESTIC_DIR)/.configured

$(pkg)-uninstall:
	$(RM) $(RESTIC_TARGET_BINARY)

$(PKG_FINISH)