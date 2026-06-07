$(call PKG_INIT_BIN, 1.74.1)
$(PKG)_SOURCE_DOWNLOAD_NAME:=v$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=aa0470151fe2e33d6bb96657892dfc4d56f92472a2dedebdda4ff296e87b79dc
$(PKG)_SITE:=https://github.com/rclone/rclone/archive/refs/tags
$(PKG)_DIR:=$(SOURCE_DIR)/rclone-$($(PKG)_VERSION)
### WEBSITE:=https://github.com/rclone/rclone
### MANPAGE:=https://rclone.org/docs/
### CHANGES:=https://github.com/rclone/rclone/releases
### CVSREPO:=https://github.com/rclone/rclone
### SUPPORT:=ircama
### STEWARD:=Ircama

$(PKG)_BINARY:=$($(PKG)_DIR)/rclone
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/rclone

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
	@echo "Building rclone with Go $(RCLONE_GO_VERSION)..."
	cd $(RCLONE_DIR); \
	export PATH=$(TOOLS_DIR)/go-host/bin:$$PATH; \
	GOOS=$(RCLONE_GO_OS) \
	GOARCH=$(RCLONE_GO_ARCH) \
	$(if $(RCLONE_GO_MIPS),GOMIPS=$(RCLONE_GO_MIPS),) \
	$(if $(RCLONE_GO_ARM),GOARM=$(RCLONE_GO_ARM),) \
	CGO_ENABLED=0 \
	go build \
		-v \
		-buildvcs=false \
		-trimpath \
		-ldflags="-s -w -X github.com/rclone/rclone/fs.Version=v$(RCLONE_VERSION)" \
		-o rclone \
		.

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	$(INSTALL_BINARY_STRIP)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(RCLONE_DIR) clean
	$(RM) $(RCLONE_BINARY) $(RCLONE_DIR)/.configured

$(pkg)-uninstall:
	$(RM) $(RCLONE_TARGET_BINARY)

$(PKG_FINISH)