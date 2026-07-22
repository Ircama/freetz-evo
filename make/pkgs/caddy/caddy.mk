$(call PKG_INIT_BIN, 2.11.2)
$(PKG)_SOURCE_DOWNLOAD_NAME:=v$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=ee12f7b5f97308708de5067deebb3d3322fc24f6d54f906a47a0a4e8db799122
$(PKG)_SITE:=https://github.com/caddyserver/caddy/archive/refs/tags
$(PKG)_DIR:=$(SOURCE_DIR)/caddy-$($(PKG)_VERSION)
### WEBSITE:=https://caddyserver.com/
### MANPAGE:=https://caddyserver.com/docs/
### CHANGES:=https://github.com/caddyserver/caddy/releases
### CVSREPO:=https://github.com/caddyserver/caddy
### SUPPORT:=ircama
### STEWARD:=Ircama

$(PKG)_BINARY:=$($(PKG)_DIR)/caddy
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/caddy

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
$(PKG)_GO_MODCACHE := $(abspath $($(PKG)_DIR)/.gomodcache)

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	@echo "Building caddy with Go $(CADDY_GO_VERSION)..."
	cd $(CADDY_DIR); \
	export PATH=$(TOOLS_DIR)/go-host/bin:$$PATH; \
	GOFLAGS=-modcacherw \
	GOMODCACHE=$(CADDY_GO_MODCACHE) \
	GOOS=$(CADDY_GO_OS) \
	GOARCH=$(CADDY_GO_ARCH) \
	$(if $(CADDY_GO_MIPS),GOMIPS=$(CADDY_GO_MIPS),) \
	$(if $(CADDY_GO_ARM),GOARM=$(CADDY_GO_ARM),) \
	CGO_ENABLED=0 \
	go build \
		-v \
		-buildvcs=false \
		-trimpath \
		-ldflags="-s -w" \
		-o caddy \
		./cmd/caddy

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	$(INSTALL_BINARY_STRIP)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(CADDY_DIR) clean
	$(RM) $(CADDY_BINARY) $(CADDY_DIR)/.configured
	$(RM) -r $(CADDY_GO_MODCACHE)

$(pkg)-uninstall:
	$(RM) $(CADDY_TARGET_BINARY)

$(PKG_FINISH)