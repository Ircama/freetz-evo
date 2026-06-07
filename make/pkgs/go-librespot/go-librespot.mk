$(call PKG_INIT_BIN, 0.7.1)
$(PKG)_SOURCE_DOWNLOAD_NAME:=v$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=25595b6dc1a4e030df74a2ca8ec9206052958b138f7453e75a0bb7233577df94
$(PKG)_SITE:=https://github.com/devgianlu/go-librespot/archive/refs/tags
$(PKG)_DIR:=$(SOURCE_DIR)/go-librespot-$($(PKG)_VERSION)
### WEBSITE:=https://github.com/devgianlu/go-librespot
### MANPAGE:=https://github.com/devgianlu/go-librespot#readme
### CHANGES:=https://github.com/devgianlu/go-librespot/releases
### CVSREPO:=https://github.com/devgianlu/go-librespot
### SUPPORT:=ircama
### STEWARD:=Ircama
### PKGSITE:=https://github.com/Ircama/freetz-evo/tree/master/make/pkgs/go-librespot/

$(PKG)_CATEGORY:=Audio

$(PKG)_BINARY:=$($(PKG)_DIR)/go-librespot
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/go-librespot

$(PKG)_GO_VERSION := 1.25.10

$(PKG)_DEPENDS_ON += go-host alsa-lib flac libogg libvorbis

$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_ARCH_MIPS
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_ARCH_ARM
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_ARCH_X86
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_ARCH_AARCH64

$(PKG)_GO_OS := linux
$(PKG)_GO_ARCH := $(FREETZ_TARGET_GO_ARCH)
$(PKG)_GO_MIPS := $(FREETZ_TARGET_GO_MIPS)
$(PKG)_GO_ARM := $(FREETZ_TARGET_GO_ARM)
$(PKG)_GO_MODCACHE := $(abspath $($(PKG)_DIR)/.gomodcache)
$(PKG)_GO_CACHE := $(abspath $($(PKG)_DIR)/.gocache)
$(PKG)_PKG_CONFIG_DIR := $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig
$(PKG)_CGO_CFLAGS := $(TARGET_CFLAGS) -I$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include
$(PKG)_CGO_LDFLAGS := -L$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib
$(PKG)_VORBIS_GO_VERSION := v0.0.0-20210911202351-b5b85f1ec645
$(PKG)_VORBIS_GO_DIR := $($(PKG)_GO_MODCACHE)/github.com/xlab/vorbis-go@$($(PKG)_VORBIS_GO_VERSION)/vorbis

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	@echo "Building go-librespot with Go $(GO_LIBRESPOT_GO_VERSION)..."
	cd $(GO_LIBRESPOT_DIR); \
		export PATH=$(abspath $(TOOLS_DIR))/go-host/bin:$$PATH; \
		export GOTOOLCHAIN=local GOFLAGS=-modcacherw GOMODCACHE=$(GO_LIBRESPOT_GO_MODCACHE) GOCACHE=$(GO_LIBRESPOT_GO_CACHE) GOOS=$(GO_LIBRESPOT_GO_OS) GOARCH=$(GO_LIBRESPOT_GO_ARCH) CC="$(TARGET_CC)" CGO_ENABLED=1 CGO_CFLAGS='$(GO_LIBRESPOT_CGO_CFLAGS)' CGO_LDFLAGS='$(GO_LIBRESPOT_CGO_LDFLAGS)' PKG_CONFIG=/usr/bin/pkg-config PKG_CONFIG_LIBDIR="$(GO_LIBRESPOT_PKG_CONFIG_DIR)" PKG_CONFIG_PATH="$(GO_LIBRESPOT_PKG_CONFIG_DIR)"; \
		if [ -n "$(GO_LIBRESPOT_GO_MIPS)" ]; then export GOMIPS=$(GO_LIBRESPOT_GO_MIPS); fi; \
		if [ -n "$(GO_LIBRESPOT_GO_ARM)" ]; then export GOARM=$(GO_LIBRESPOT_GO_ARM); fi; \
		go mod download; \
		chmod u+w '$(GO_LIBRESPOT_VORBIS_GO_DIR)'; \
		chmod u+w '$(GO_LIBRESPOT_VORBIS_GO_DIR)/vorbis.go' '$(GO_LIBRESPOT_VORBIS_GO_DIR)/cgo_helpers.go'; \
		sed -i -e 's/0x7fffffff/0x3fffffff/g' \
			'$(GO_LIBRESPOT_VORBIS_GO_DIR)/vorbis.go' \
			'$(GO_LIBRESPOT_VORBIS_GO_DIR)/cgo_helpers.go'; \
		go build \
			-v \
			-buildvcs=false \
			-trimpath \
			-ldflags="-s -w" \
			-o go-librespot \
			./cmd/daemon

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	$(INSTALL_BINARY_STRIP)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(GO_LIBRESPOT_DIR) clean
	$(RM) $(GO_LIBRESPOT_BINARY) $(GO_LIBRESPOT_DIR)/.configured
	$(RM) -r $(GO_LIBRESPOT_GO_MODCACHE) $(GO_LIBRESPOT_GO_CACHE)

$(pkg)-uninstall:
	$(RM) $(GO_LIBRESPOT_TARGET_BINARY)

$(PKG_FINISH)