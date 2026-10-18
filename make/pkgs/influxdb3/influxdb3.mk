$(call PKG_INIT_BIN, 3.12.1)
### STEWARD:=Ircama
$(PKG)_CATEGORY_PKGS:=Home Automation

$(PKG)_SOURCE_DOWNLOAD_NAME:=v$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=e8adf1920dd826db9774cfa8f3a97d8cbc6471777eebcdda9448916b82abe23c
$(PKG)_SITE:=https://github.com/influxdata/influxdb/archive/refs/tags
$(PKG)_DIR:=$(SOURCE_DIR)/influxdb3-$($(PKG)_VERSION)
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/influxdb3
### WEBSITE:=https://www.influxdata.com/
### CHANGES:=https://github.com/influxdata/influxdb/releases
### CVSREPO:=https://github.com/influxdata/influxdb

include $(MAKE_DIR)/include/650-rust-cargo.mk
$(eval $(call RUST_TARGET_VARS))
$(eval $(call RUST_CARGO_BUILD_STD_VARS))
$(PKG)_BINARY:=$($(PKG)_DIR)/target/$($(PKG)_RUST_TARGET_DIR)/release/influxdb3
$(eval $(call RUST_CARGO_HOME_VARS))
$(eval $(call RUST_DEPENDS_VARS))
$(PKG)_CACHE_DIR:=$(abspath $(TOPDIR)/$(BUILD_DIR))/cargo-influxdb3-cache/$($(PKG)_VERSION)-$($(PKG)_RUST_TARGET_DIR)
$(PKG)_CARGO_PATCH_SOURCES:=$($(PKG)_MAKE_DIR)/tools/apply-cargo-patches.py $(wildcard $($(PKG)_MAKE_DIR)/cargo-patches/*.patch)
$(PKG)_DEPENDS_ON += cmake-host protobuf-host python3

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$(pkg)-download:
	@$(call _ECHO,downloading)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured $(INFLUXDB3_CARGO_PATCH_SOURCES)
	cd $(INFLUXDB3_DIR); \
	export PATH=$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH; \
	export RUSTUP_HOME="$(HOME)/.rustup"; \
	export HOME="$(abspath $(INFLUXDB3_DIR))"; \
	export CARGO_HOME="$(INFLUXDB3_CARGO_HOME)"; \
	export CARGO_BUILD_JOBS=1; \
	export CARGO_PROFILE_RELEASE_LTO=false CARGO_PROFILE_RELEASE_CODEGEN_UNITS=256; \
	export CARGO_PROFILE_RELEASE_OPT_LEVEL=s CARGO_PROFILE_RELEASE_DEBUG=0; \
	export PYO3_CROSS=1 PYO3_CROSS_LIB_DIR="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib"; \
	export PROTOC="$(PROTOBUF_HOST_TARGET_BINARY)" PROTOC_INCLUDE="$(PROTOBUF_HOST_INSTALL_DIR)/include"; \
	export CC_$(INFLUXDB3_RUST_ENV_TARGET)="$(TARGET_CROSS)gcc"; \
	export CXX_$(INFLUXDB3_RUST_ENV_TARGET)="$(TARGET_CROSS)g++"; \
	export AR_$(INFLUXDB3_RUST_ENV_TARGET)="$(TARGET_CROSS)ar"; \
	mkdir -p "$$CARGO_HOME" "$(INFLUXDB3_CACHE_DIR)/cargo/registry" "$(INFLUXDB3_CACHE_DIR)/cargo/git" "$(INFLUXDB3_CACHE_DIR)/target"; \
	for cache in registry git; do \
		if [ -e "$$CARGO_HOME/$$cache" ] && [ ! -L "$$CARGO_HOME/$$cache" ]; then echo "Refusing to overwrite an existing InfluxDB Cargo cache: $$cache" >&2; exit 1; fi; \
		ln -sfn "$(INFLUXDB3_CACHE_DIR)/cargo/$$cache" "$$CARGO_HOME/$$cache" || exit 1; \
	done; \
	if [ -e target ] && [ ! -L target ]; then echo "Refusing to overwrite existing InfluxDB build artifacts" >&2; exit 1; fi; \
	ln -sfn "$(INFLUXDB3_CACHE_DIR)/target" target || exit 1; \
	printf '[target.%s]\nlinker = "%s"\nar = "%s"\nrustflags = ["-C", "link-arg=-latomic", "-C", "link-arg=-Wl,-no-pie", "-Zthreads=1"]\n' \
		"$(INFLUXDB3_RUST_TARGET_DIR)" "$(TARGET_CROSS)gcc" "$(TARGET_CROSS)ar" > "$$CARGO_HOME/config.toml"; \
	python3 "$(abspath $(INFLUXDB3_MAKE_DIR))/tools/apply-cargo-patches.py" --workspace . --cargo-home "$$CARGO_HOME" || exit 1; \
	cargo +nightly fetch --locked --target "$(INFLUXDB3_RUST_TARGET_DIR)" || exit 1; \
	python3 "$(abspath $(INFLUXDB3_MAKE_DIR))/tools/apply-cargo-patches.py" --workspace . --cargo-home "$$CARGO_HOME" || exit 1; \
	$(call GETRANDOM_APPLY_UCLIBC_MIPS_SYSCALL_PATCH__INT,0.3.4) \
	$(call GETRANDOM_APPLY_UCLIBC_MIPS_SYSCALL_PATCH__INT,0.4.2) \
	$(call GETRANDOM_APPLY_UCLIBC_MIPS_SYSCALL_PATCH__INT,0.4.3) \
	$(call RUSTIX_APPLY_UCLIBC_PATCHES_RAW_DEP__INT,1.1.4) \
	cargo +nightly rustc --locked --release --no-default-features -p influxdb3 --bin influxdb3 \
		$(INFLUXDB3_CARGO_BUILD_STD_FLAGS) --target "$(INFLUXDB3_RUST_TARGET_ARG)" \
		-- -C "link-arg=-Wl,--dynamic-linker=$(FREETZ_LIBRARY_DIR)/ld-uClibc.so.1"

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	$(INSTALL_BINARY_STRIP)

$(pkg): $($(PKG)_BINARY)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	$(RM) $(INFLUXDB3_BINARY) $(INFLUXDB3_TARGET_BINARY)

$(pkg)-cargo-clean:
	$(RM) -r $(INFLUXDB3_CACHE_DIR)/target $(INFLUXDB3_DIR)/target

.PHONY: $(pkg)-cargo-clean

$(pkg)-uninstall:
	$(RM) $(INFLUXDB3_TARGET_BINARY)

$(PKG_FINISH)