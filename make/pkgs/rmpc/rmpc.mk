$(call PKG_INIT_BIN, 0.11.0)
# Rust/Cargo cross-build requires a recent toolchain: gated by "depends on
# FREETZ_TARGET_UCLIBC_1_0_58_MIN" in Config.in (fails on 0.9.x/1.0.14).
include $(MAKE_DIR)/include/650-rust-cargo.mk
$(PKG)_SOURCE_DOWNLOAD_NAME:=v$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=930019066228d18e9530a8c0d77f10e231ab5efbbbca73b331efcd6fbb47557d
$(PKG)_SITE:=https://github.com/mierak/rmpc/archive/refs/tags
$(PKG)_DIR:=$(SOURCE_DIR)/rmpc-$($(PKG)_VERSION)
### WEBSITE:=https://github.com/mierak/rmpc
### CHANGES:=https://github.com/mierak/rmpc/releases

$(PKG)_CATEGORY_PKGS:=Audio

RMPC_RUST_TARGET_DIR:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(basename $(notdir $(RUST_TARGET_CUSTOM_NAME))))
RMPC_RUST_TARGET_ARG:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_SPEC_FILE))
RMPC_RUST_ENV_TARGET:=$(subst -,_,$(RMPC_RUST_TARGET_DIR))
RMPC_CARGO_BUILD_STD_FLAGS:=-Z build-std=std\,panic_abort$(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)), -Zjson-target-spec)
RMPC_CARGO_BUILD_CMD:=$(if $(RUST_TARGET_NEEDS_STD_BUILD),cargo +nightly build --release --locked $(RMPC_CARGO_BUILD_STD_FLAGS),cargo build --release --locked)
RMPC_CARGO_HOME:=$(abspath $(RMPC_DIR)/.cargo)
$(PKG)_BINARY:=$(RMPC_DIR)/target/$(RMPC_RUST_TARGET_DIR)/release/rmpc
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/rmpc

$(PKG)_DEPENDS_ON += rust-host
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_BUILTIN_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_CUSTOM_TARGET

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_BINARY): $(RMPC_DIR)/.configured
	cd $(RMPC_DIR); \
	export PATH=$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH; \
	export HOME="$(abspath $(RMPC_DIR))"; \
	export CARGO_HOME="$(RMPC_CARGO_HOME)"; \
	export RUSTUP_HOME="$(HOME)/.rustup"; \
	export CC_$(RMPC_RUST_ENV_TARGET)="$(TARGET_CROSS)gcc"; \
	export CXX_$(RMPC_RUST_ENV_TARGET)="$(TARGET_CROSS)g++"; \
	export AR_$(RMPC_RUST_ENV_TARGET)="$(TARGET_CROSS)ar"; \
	export RANLIB_$(RMPC_RUST_ENV_TARGET)="$(TARGET_CROSS)ranlib"; \
	export RUSTFLAGS="-C link-arg=-Wl,-no-pie"; \
	mkdir -p "$$CARGO_HOME"; \
	printf '[target.%s]\nlinker = "%s"\nar = "%s"\n' \
		"$(RMPC_RUST_TARGET_DIR)" \
		"$(TARGET_CROSS)gcc" \
		"$(TARGET_CROSS)ar" \
		> "$$CARGO_HOME/config.toml"; \
	cargo$(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)), +nightly) fetch --locked --target "$(RMPC_RUST_TARGET_ARG)" $(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)),-Zjson-target-spec); \
	$(call RUST_APPLY_UCLIBC_X86_LIBC_PATCH) \
	$(call RUSTIX_APPLY_UCLIBC_PATCHES_RAW_DEP__INT,1.1.3) \
	$(call RUSTIX_APPLY_UCLIBC_PATCHES_LINUX_KERNEL__INT,1.1.3) \
	$(call GETRANDOM_APPLY_UCLIBC_MIPS_SYSCALL_PATCH__INT,0.3.4) \
	$(RMPC_CARGO_BUILD_CMD) --target "$(RMPC_RUST_TARGET_ARG)" --bin rmpc

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	$(INSTALL_BINARY_STRIP)

$(pkg)-clean:
	cd $(RMPC_DIR) && cargo clean 2>/dev/null || true
	$(RM) $($(PKG)_BINARY) $(RMPC_DIR)/.configured $(RMPC_DIR)/.cargo/config.toml

$(pkg)-uninstall:
	$(RM) $(RMPC_TARGET_BINARY)

$(PKG_FINISH)
