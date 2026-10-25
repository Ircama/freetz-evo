# ble2uart_gateway -- BLE advertisement gateway for the ESP32 ADV_BLE2UART firmware.
#
# The Rust sources live in the src/ directory of the package in the repository
# and are copied into the freetz owned source directory before the build,
# because freetz removes $(PKG)_DIR while preparing a package.
$(call PKG_INIT_BIN, 0.1)
### STEWARD:=Ircama
$(PKG)_CATEGORY_PKGS:=Home Automation

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/ble2uart-gateway
$(PKG)_DEPENDS_ON += $(if $(FREETZ_SEPARATE_AVM_UCLIBC),patchelf-target-host)

$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_BLE2UART_GATEWAY

include $(MAKE_DIR)/include/650-rust-cargo.mk

$(eval $(call RUST_TARGET_VARS))
$(eval $(call RUST_CARGO_BUILD_STD_VARS))

$(PKG)_BINARY:=$($(PKG)_DIR)/src/target/$($(PKG)_RUST_TARGET_DIR)/release/ble2uart-gateway
$(PKG)_CARGO_HOME:=$(abspath $($(PKG)_DIR)/src/.cargo)
$(eval $(call RUST_DEPENDS_VARS))

# ---------------------------------------------------------------------------
# Download phase: there is no tarball, the dependencies come from crates.io and
# are pinned by src/Cargo.lock. The cache below is filled once by
# `make ble2uart_gateway-download` (or by `make sources`) and the build hard-links it
# + builds --offline, so a package build never touches the network.
# ---------------------------------------------------------------------------
BLE2UART_GATEWAY_CARGO_CACHE:=$(abspath $(TOPDIR)/$(BUILD_DIR))/cargo-ble-cache
BLE2UART_GATEWAY_CARGO_DL_DIR:=$(BLE2UART_GATEWAY_CARGO_CACHE)/$(pkg)
BLE2UART_GATEWAY_CARGO_DL_STAMP:=$(BLE2UART_GATEWAY_CARGO_CACHE)/$(pkg).fetched

# ---------------------------------------------------------------------------
# Optional Theengs Decoder (GPL-3.0-or-later) as a static library.
# The C++ sources are pinned by revision and checksum; the library is linked
# only when FREETZ_PACKAGE_BLE2UART_GATEWAY_THEENGS is enabled, and it enables
# `decoder: theengs|both` in the YAML.
# ---------------------------------------------------------------------------
BLE2UART_GATEWAY_THEENGS_REVISION:=895a6b5461af29952dbb59286751591db933ee4c
BLE2UART_GATEWAY_THEENGS_SHA256:=7a78815bd41d53108d64eb40192e9ca0ef6dcd03502ae264c84278040dd022a5
BLE2UART_GATEWAY_ARDUINOJSON_REVISION:=b810833145e3cdab738fb4a45d7d4010a0e13f6d
BLE2UART_GATEWAY_ARDUINOJSON_SHA256:=8e3c9e26f660a93a7204f594d7b0eedf704fce5c796095e99328cc2de1d93241
BLE2UART_GATEWAY_THEENGS_DIR:=$(abspath $(TOPDIR)/$(SOURCE_DIR))/$(pkg)_theengs
BLE2UART_GATEWAY_THEENGS_LIB_DIR:=$(BLE2UART_GATEWAY_THEENGS_DIR)
BLE2UART_GATEWAY_THEENGS_LIB:=$(BLE2UART_GATEWAY_THEENGS_DIR)/libtheengs.a
BLE2UART_GATEWAY_THEENGS_SRC:=decoder-$(BLE2UART_GATEWAY_THEENGS_REVISION)
BLE2UART_GATEWAY_THEENGS_JSON:=ArduinoJson-$(BLE2UART_GATEWAY_ARDUINOJSON_REVISION)

ifeq ($(FREETZ_PACKAGE_BLE2UART_GATEWAY_THEENGS),y)
BLE2UART_GATEWAY_CARGO_FEATURES:=freetz theengs
BLE2UART_GATEWAY_THEENGS_DEP:=$(BLE2UART_GATEWAY_THEENGS_LIB)
else
BLE2UART_GATEWAY_CARGO_FEATURES:=freetz
BLE2UART_GATEWAY_THEENGS_DEP:=
endif

$(BLE2UART_GATEWAY_THEENGS_LIB):
	@$(call _ECHO,preparing)
	set -e; mkdir -p $(BLE2UART_GATEWAY_THEENGS_DIR); cd $(BLE2UART_GATEWAY_THEENGS_DIR); \
	export PATH="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH"; \
	fetch() { \
		if [ ! -f "$$2" ] || ! echo "$$3  $$2" | sha256sum -c --status 2>/dev/null; then \
			curl -fsL --retry 3 -o "$$2" "$$1"; \
		fi; \
		echo "$$3  $$2" | sha256sum -c -; \
	}; \
	fetch https://github.com/theengs/decoder/archive/$(BLE2UART_GATEWAY_THEENGS_REVISION).tar.gz decoder.tar.gz $(BLE2UART_GATEWAY_THEENGS_SHA256); \
	fetch https://github.com/bblanchon/ArduinoJson/archive/$(BLE2UART_GATEWAY_ARDUINOJSON_REVISION).tar.gz arduinojson.tar.gz $(BLE2UART_GATEWAY_ARDUINOJSON_SHA256); \
	rm -rf $(BLE2UART_GATEWAY_THEENGS_SRC) $(BLE2UART_GATEWAY_THEENGS_JSON); \
	tar xzf decoder.tar.gz $(BLE2UART_GATEWAY_THEENGS_SRC)/src $(BLE2UART_GATEWAY_THEENGS_SRC)/include; \
	tar xzf arduinojson.tar.gz $(BLE2UART_GATEWAY_THEENGS_JSON)/src $(BLE2UART_GATEWAY_THEENGS_JSON)/LICENSE.md; \
	$(TARGET_CROSS)g++ -std=c++17 -Os -fno-exceptions -fno-rtti \
		-I $(BLE2UART_GATEWAY_THEENGS_SRC)/src \
		-I $(BLE2UART_GATEWAY_THEENGS_JSON)/src \
		-I $(BLE2UART_GATEWAY_THEENGS_SRC)/include \
		-c $(BLE2UART_GATEWAY_THEENGS_SRC)/src/decoder.cpp -o decoder.o; \
	$(TARGET_CROSS)g++ -std=c++17 -Os -fno-exceptions -fno-rtti \
		-I $(BLE2UART_GATEWAY_THEENGS_SRC)/src \
		-I $(BLE2UART_GATEWAY_THEENGS_JSON)/src \
		-I $(BLE2UART_GATEWAY_THEENGS_SRC)/include \
		-c $(BLE2UART_GATEWAY_THEENGS_SRC)/src/decoder_c.cpp -o decoder_c.o; \
	$(TARGET_CROSS)ar rcs libtheengs.a decoder.o decoder_c.o

BLE2UART_GATEWAY_SOURCES := \
	$(BLE2UART_GATEWAY_MAKE_DIR)/src/README.md \
	$(BLE2UART_GATEWAY_MAKE_DIR)/src/build.rs \
	$(BLE2UART_GATEWAY_MAKE_DIR)/src/Cargo.toml \
	$(BLE2UART_GATEWAY_MAKE_DIR)/src/Cargo.lock \
	$(wildcard $(BLE2UART_GATEWAY_MAKE_DIR)/src/spec/*.yaml) \
	$(wildcard $(BLE2UART_GATEWAY_MAKE_DIR)/src/spec/*.tsv) \
	$(wildcard $(BLE2UART_GATEWAY_MAKE_DIR)/src/tests/*.json) \
	$(wildcard $(BLE2UART_GATEWAY_MAKE_DIR)/src/src/*.rs) \
	$(wildcard $(BLE2UART_GATEWAY_MAKE_DIR)/src/src/codec/*.rs) \
	$(wildcard $(BLE2UART_GATEWAY_MAKE_DIR)/src/src/frontend/*.rs)

# These recipes expand after PKG_FINISH clears the global package context.
$($(PKG)_DIR)/.unpacked $(BLE2UART_GATEWAY_CARGO_DL_STAMP) $($(PKG)_BINARY): private pkg := $(pkg)
$($(PKG)_DIR)/.unpacked $(BLE2UART_GATEWAY_CARGO_DL_STAMP) $($(PKG)_BINARY): private PKG_TYPE := $(PKG_TYPE)

# The sources are copied from the package directory into the (freetz owned)
# source directory.
$($(PKG)_DIR)/.unpacked: $(BLE2UART_GATEWAY_SOURCES) | $(SOURCE_DIR)
	@$(call _ECHO,preparing)
	mkdir -p $(BLE2UART_GATEWAY_DIR)/src/src
	cp $(BLE2UART_GATEWAY_MAKE_DIR)/src/Cargo.toml $(BLE2UART_GATEWAY_MAKE_DIR)/src/Cargo.lock $(BLE2UART_GATEWAY_MAKE_DIR)/src/README.md $(BLE2UART_GATEWAY_MAKE_DIR)/src/build.rs $(BLE2UART_GATEWAY_DIR)/src/
	cp $(BLE2UART_GATEWAY_MAKE_DIR)/src/src/*.rs $(BLE2UART_GATEWAY_DIR)/src/src/
	mkdir -p $(BLE2UART_GATEWAY_DIR)/src/spec $(BLE2UART_GATEWAY_DIR)/src/tests
	cp $(BLE2UART_GATEWAY_MAKE_DIR)/src/spec/*.yaml $(BLE2UART_GATEWAY_MAKE_DIR)/src/spec/*.tsv $(BLE2UART_GATEWAY_DIR)/src/spec/
	cp $(BLE2UART_GATEWAY_MAKE_DIR)/src/tests/*.json $(BLE2UART_GATEWAY_DIR)/src/tests/
	@touch $@

$(PKG_CONFIGURED_NOP)

$(pkg)-download: $(BLE2UART_GATEWAY_CARGO_DL_STAMP)
$(if $(BLE2UART_GATEWAY_THEENGS_DEP),$(pkg)-download: $(BLE2UART_GATEWAY_THEENGS_LIB))

$(BLE2UART_GATEWAY_CARGO_DL_STAMP): $(BLE2UART_GATEWAY_SOURCES)
	@$(call _ECHO,downloading)
	rm -rf $(BLE2UART_GATEWAY_CARGO_DL_DIR)
	mkdir -p $(BLE2UART_GATEWAY_CARGO_DL_DIR)/src
	cp $(BLE2UART_GATEWAY_MAKE_DIR)/src/Cargo.toml $(BLE2UART_GATEWAY_MAKE_DIR)/src/Cargo.lock $(BLE2UART_GATEWAY_MAKE_DIR)/src/README.md $(BLE2UART_GATEWAY_MAKE_DIR)/src/build.rs $(BLE2UART_GATEWAY_CARGO_DL_DIR)/
	cp $(BLE2UART_GATEWAY_MAKE_DIR)/src/src/*.rs $(BLE2UART_GATEWAY_CARGO_DL_DIR)/src/
	mkdir -p $(BLE2UART_GATEWAY_CARGO_DL_DIR)/spec
	cp $(BLE2UART_GATEWAY_MAKE_DIR)/src/spec/*.yaml $(BLE2UART_GATEWAY_MAKE_DIR)/src/spec/*.tsv $(BLE2UART_GATEWAY_CARGO_DL_DIR)/spec/
	cd $(BLE2UART_GATEWAY_CARGO_DL_DIR); \
	export PATH=$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH; \
	export HOME="$(BLE2UART_GATEWAY_CARGO_CACHE)"; \
	export CARGO_HOME="$$HOME/.cargo"; \
	export RUSTUP_HOME="$(HOME)/.rustup"; \
	mkdir -p "$$CARGO_HOME"; \
	cargo +nightly fetch --locked $(BLE2UART_GATEWAY_CARGO_BUILD_STD_FLAGS) --target "$(BLE2UART_GATEWAY_RUST_TARGET_DIR)" && \
	cargo +nightly fetch --locked && \
	$(call RUSTIX_APPLY_UCLIBC_PATCHES_LIBC_NORAW__INT,1.1.5) \
	$(call GETRANDOM_APPLY_UCLIBC_MIPS_SYSCALL_PATCH__INT,0.3.4) \
	$(call GETRANDOM_APPLY_UCLIBC_MIPS_SYSCALL_PATCH__INT,0.4.3) \
	true
	@touch $@

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY) | $(if $(FREETZ_SEPARATE_AVM_UCLIBC),$(TOOLS_DIR)/patchelf-target)
	set -e; $(INSTALL_BINARY_STRIP)

# `-Z build-std` is required for mips-unknown-linux-uclibc. Build serially:
# the Matter SDK's generated cluster code has significant peak memory use.
$($(PKG)_BINARY): $($(PKG)_DIR)/.configured $(BLE2UART_GATEWAY_THEENGS_DEP) | $(BLE2UART_GATEWAY_CARGO_DL_STAMP)
	@$(call _ECHO,building)
	cd $(BLE2UART_GATEWAY_DIR)/src; \
	export PATH=$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH; \
	export HOME="$(abspath $(BLE2UART_GATEWAY_DIR)/src)"; \
	export CARGO_HOME="$(BLE2UART_GATEWAY_CARGO_HOME)"; \
	export RUSTUP_HOME="$(HOME)/.rustup"; \
	mkdir -p "$$CARGO_HOME"; \
	$(call CARGO_LINK_DL_CACHE__INT,$(BLE2UART_GATEWAY_CARGO_CACHE)/.cargo,$$CARGO_HOME) \
	printf '[target.%s]\nlinker = "%s"\nar = "%s"\nrustflags = ["-C", "link-arg=-Wl,-no-pie", "-Zthreads=1"]\n' \
		"$(BLE2UART_GATEWAY_RUST_TARGET_DIR)" \
		"$(TARGET_CROSS)gcc" \
		"$(TARGET_CROSS)ar" \
		> "$$CARGO_HOME/config.toml"; \
	export CARGO_BUILD_JOBS=1; \
	export CC_$(BLE2UART_GATEWAY_RUST_ENV_TARGET)="$(TARGET_CROSS)gcc"; \
	export AR_$(BLE2UART_GATEWAY_RUST_ENV_TARGET)="$(TARGET_CROSS)ar"; \
        $(if $(BLE2UART_GATEWAY_THEENGS_DEP),export THEENGS_LIB_DIR="$(BLE2UART_GATEWAY_THEENGS_LIB_DIR)";) \
        cargo +nightly fetch --locked --offline --target "$(BLE2UART_GATEWAY_RUST_TARGET_DIR)" && \
        $(call RUSTIX_APPLY_UCLIBC_PATCHES_LIBC_NORAW__INT,1.1.5) \
        $(call GETRANDOM_APPLY_UCLIBC_MIPS_SYSCALL_PATCH__INT,0.3.4) \
        $(call GETRANDOM_APPLY_UCLIBC_MIPS_SYSCALL_PATCH__INT,0.4.3) \
        cargo +nightly build --locked --offline --release $(BLE2UART_GATEWAY_CARGO_BUILD_STD_FLAGS) \
                --features "$(BLE2UART_GATEWAY_CARGO_FEATURES)" --target "$(BLE2UART_GATEWAY_RUST_TARGET_ARG)"

# Static files are staged through an explicit target: the generic
# $($(PKG)_TARGET_DIR)/root rule has only an order-only prerequisite, so a
# rebuild would keep stale copies of files/root otherwise (that is how an image
# once ended up with a stale rc script and no web menu entry).
$(PKG)_STAGING_SOURCES := \
	$(BLE2UART_GATEWAY_MAKE_DIR)/files/.language \
	$(BLE2UART_GATEWAY_MAKE_DIR)/files/root/etc/default.ble2uart_gateway/ble2uart_gateway.cfg \
	$(BLE2UART_GATEWAY_MAKE_DIR)/files/root/etc/default.ble2uart_gateway/ble2uart_gateway.save \
	$(BLE2UART_GATEWAY_MAKE_DIR)/files/root/etc/init.d/rc.ble2uart_gateway \
	$(BLE2UART_GATEWAY_MAKE_DIR)/files/root/usr/lib/cgi-bin/ble2uart_gateway.cgi \
	$(BLE2UART_GATEWAY_MAKE_DIR)/files/root/usr/lib/cgi-bin/ble2uart_gateway/api.cgi \
        $(BLE2UART_GATEWAY_MAKE_DIR)/files/root/usr/lib/cgi-bin/ble2uart_gateway/portal.cgi \
        $(BLE2UART_GATEWAY_MAKE_DIR)/files/root/usr/mww/ble2uart_gateway/mode-yaml.js \
        $(BLE2UART_GATEWAY_MAKE_DIR)/files/root/usr/mww/ble2uart_gateway/portal.css \
        $(BLE2UART_GATEWAY_MAKE_DIR)/files/root/usr/mww/ble2uart_gateway/portal.js

$($(PKG)_STAGING_TARGET): $($(PKG)_STAGING_SOURCES)
	mkdir -p $(BLE2UART_GATEWAY_TARGET_DIR)/root
	$(call COPY_USING_TAR,$(BLE2UART_GATEWAY_MAKE_DIR)/files,$(BLE2UART_GATEWAY_TARGET_DIR))
	chmod 755 \
		$(BLE2UART_GATEWAY_DEST_DIR)/etc/init.d/rc.ble2uart_gateway \
		$(BLE2UART_GATEWAY_DEST_DIR)/etc/default.ble2uart_gateway/ble2uart_gateway.save \
		$(BLE2UART_GATEWAY_DEST_DIR)/usr/lib/cgi-bin/ble2uart_gateway.cgi \
                $(BLE2UART_GATEWAY_DEST_DIR)/usr/lib/cgi-bin/ble2uart_gateway/api.cgi \
                $(BLE2UART_GATEWAY_DEST_DIR)/usr/lib/cgi-bin/ble2uart_gateway/portal.cgi
$(pkg)-precompiled: $($(PKG)_TARGET_BINARY) $($(PKG)_STAGING_TARGET)

$(pkg)-clean:
	$(RM) -r $(BLE2UART_GATEWAY_DIR)/src/target

$(pkg)-uninstall:
	$(RM) $($(PKG)_TARGET_BINARY)

$(PKG_FINISH)
