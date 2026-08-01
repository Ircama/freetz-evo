$(call PKG_INIT_BIN, 0.23.4)
include $(MAKE_DIR)/include/650-rust-cargo.mk
$(PKG)_SOURCE_DOWNLOAD_NAME:=v0.23.4.tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=9fbcad518b8a2095206ac385329ca62d216bf9fdc652dde2d082fcb37c309635
$(PKG)_SITE:=https://github.com/eza-community/eza/archive/refs/tags
$(PKG)_DIR:=$(SOURCE_DIR)/eza-0.23.4
### WEBSITE:=https://github.com/eza-community/eza
### CHANGES:=https://github.com/eza-community/eza/releases
### CVSREPO:=https://github.com/eza-community/eza

EZA_RUST_TARGET_DIR:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(basename $(notdir $(RUST_TARGET_CUSTOM_NAME))))
EZA_RUST_TARGET_ARG:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_SPEC_FILE))
EZA_CARGO_BUILD_STD_FLAGS:=-Z build-std=std\,panic_abort$(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)), -Zjson-target-spec)
EZA_CARGO_BUILD_CMD:=$(if $(RUST_TARGET_NEEDS_STD_BUILD),cargo +nightly build --release --locked $(EZA_CARGO_BUILD_STD_FLAGS),cargo build --release --locked)
EZA_CARGO_HOME:=$(abspath $(EZA_DIR)/.cargo)
EZA_MAKE_DIR:=$(abspath $(MAKE_DIR)/pkgs/eza)
EZA_PATCH_SCRIPT:=$(EZA_MAKE_DIR)/patch-rustix-uclibc.sh
$(PKG)_BINARY:=$(EZA_DIR)/target/$(EZA_RUST_TARGET_DIR)/release/eza
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/eza

$(eval $(call RUST_DEPENDS_VARS))

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_BINARY): $(EZA_DIR)/.configured
	cd $(EZA_DIR); \
	export PATH=$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH; \
	export HOME="$(abspath $(EZA_DIR))"; \
	export CARGO_HOME="$(EZA_CARGO_HOME)"; \
	export RUSTUP_HOME="$(HOME)/.rustup"; \
	mkdir -p "$$CARGO_HOME"; \
	tar -xzf $(abspath $(DL_DIR)/$(EZA_SOURCE)) -C $(abspath $(EZA_DIR)) --strip-components=1 $(notdir $(EZA_DIR))/Cargo.lock; \
	printf '[target.%s]\nlinker = "%s"\nar = "%s"\n' \
		"$(EZA_RUST_TARGET_DIR)" \
		"$(TARGET_CROSS)gcc" \
		"$(TARGET_CROSS)ar" \
		> "$$CARGO_HOME/config.toml"; \
	cargo$(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)), +nightly) fetch --locked --target "$(EZA_RUST_TARGET_ARG)" $(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)),-Zjson-target-spec); \
	$(call RUST_APPLY_UCLIBC_X86_LIBC_PATCH) \
	echo "Preparing persistent patched rustix..."; \
	rustix_src="$$(find "$$CARGO_HOME/registry/src" -type d -name 'rustix-1.1.2' 2>/dev/null | head -1)"; \
	if [ -n "$$rustix_src" ] && [ ! -d "$$CARGO_HOME/rustix-1.1.2-patched" ]; then \
		cp -a "$$rustix_src" "$$CARGO_HOME/rustix-1.1.2-patched"; \
		chmod -R u+w "$$CARGO_HOME/rustix-1.1.2-patched"; \
	fi; \
	echo "Running uClibc patch script..."; \
	sh "$(EZA_PATCH_SCRIPT)"; \
	echo "Writing final cargo config with [patch]..."; \
	printf '[target.%s]\nlinker = "%s"\nar = "%s"\n\n[patch.crates-io]\nrustix = { path = "%s/rustix-1.1.2-patched" }\n' \
		"$(EZA_RUST_TARGET_DIR)" \
		"$(TARGET_CROSS)gcc" \
		"$(TARGET_CROSS)ar" \
		"$$CARGO_HOME" > "$$CARGO_HOME/config.toml"; \
	echo "Updating lock file with patch..."; \
	cargo$(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)), +nightly) generate-lockfile --offline; \
	$(EZA_CARGO_BUILD_CMD) --target "$(EZA_RUST_TARGET_ARG)" --bin eza --no-default-features

$(eval $(call INSTALL_BINARY_STRIP_RULE,$($(PKG)_BINARY),/usr/bin))

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(EZA_DIR) clean
	$(RM) -r $($(PKG)_BINARY) $(EZA_DIR)/.configured $(EZA_CARGO_HOME) $(EZA_DIR)/target

$(pkg)-uninstall:
	$(RM) $($(PKG)_TARGET_BINARY)

$(PKG_FINISH)