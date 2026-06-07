$(call PKG_INIT_BIN, 0.9.0)
$(PKG)_SOURCE_DOWNLOAD_NAME:=v0.9.0.tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=43527a78ba2e5e43a7ebd8d0da8b5af17a72455c5f88b4d1134f34908a594239
$(PKG)_SITE:=https://github.com/PaulJuliusMartinez/jless/archive/refs/tags
$(PKG)_DIR:=$(SOURCE_DIR)/jless-v0.9.0
### WEBSITE:=https://github.com/PaulJuliusMartinez/jless
### CHANGES:=https://github.com/PaulJuliusMartinez/jless/releases
### CVSREPO:=https://github.com/PaulJuliusMartinez/jless

JLESS_RUST_TARGET_DIR:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(basename $(notdir $(RUST_TARGET_CUSTOM_NAME))))
JLESS_RUST_TARGET_ARG:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_SPEC_FILE))
JLESS_CARGO_BUILD_STD_FLAGS:=-Z build-std=std\,panic_abort
JLESS_CARGO_BUILD_CMD:=$(if $(RUST_TARGET_NEEDS_STD_BUILD),cargo +nightly build --release --locked $(JLESS_CARGO_BUILD_STD_FLAGS),cargo build --release --locked)
JLESS_CARGO_HOME:=$(abspath $(JLESS_DIR)/.cargo)
$(PKG)_BINARY:=$(JLESS_DIR)/target/$(JLESS_RUST_TARGET_DIR)/release/jless
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/jless

$(PKG)_DEPENDS_ON += rust-host
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_BUILTIN_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_CUSTOM_TARGET

include $(MAKE_DIR)/include/650-rust-cargo.mk

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_BINARY): $(JLESS_DIR)/.configured
	cd $(JLESS_DIR); \
	export PATH=$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH; \
	export HOME="$(abspath $(JLESS_DIR))"; \
	export CARGO_HOME="$(JLESS_CARGO_HOME)"; \
	export RUSTUP_HOME="$(HOME)/.rustup"; \
	mkdir -p "$$CARGO_HOME"; \
	printf '[target.%s]\nlinker = "%s"\nar = "%s"\n' \
		"$(JLESS_RUST_TARGET_DIR)" \
		"$(TARGET_CROSS)gcc" \
		"$(TARGET_CROSS)ar" \
		> "$$CARGO_HOME/config.toml"; \
	cargo fetch --locked --target "$(JLESS_RUST_TARGET_ARG)"; \
	cargo update -p libc --precise 0.2.177; \
	$(call NIX_APPLY_UCLIBC_MIPS_PATCHES_022__INT,0.22.1) \
	perl -0pi -e 's/^extern crate libc_stdhandle;\n//m' src/main.rs; \
	perl -0pi -e 's/let _ = libc::freopen\(filename\.as_ptr\(\), path\.as_ptr\(\), libc_stdhandle::stdin\(\)\);/let stdin_stream = libc::fdopen(libc::STDIN_FILENO, path.as_ptr());\n        if !stdin_stream.is_null() {\n            let _ = libc::freopen(filename.as_ptr(), path.as_ptr(), stdin_stream);\n        }/' src/input.rs; \
	if ! grep -q 'Clipboard support is unavailable on this target' src/app.rs; then \
		perl -0pi -e 's/use clipboard::\{ClipboardContext, ClipboardProvider\};/#[cfg(not(all(target_os = "linux", target_env = "uclibc")))]\nuse clipboard::{ClipboardContext, ClipboardProvider};\n#[cfg(all(target_os = "linux", target_env = "uclibc"))]\n#[derive(Debug)]\nstruct ClipboardContext;\n#[cfg(all(target_os = "linux", target_env = "uclibc"))]\nimpl ClipboardContext {\n    fn set_contents(&mut self, _content: String) -> Result<(), Box<dyn Error>> {\n        Err(Box::new(io::Error::new(\n            io::ErrorKind::Unsupported,\n            "Clipboard support is unavailable on this target",\n        )))\n    }\n}/' src/app.rs; \
		perl -0pi -e 's/clipboard_context: ClipboardProvider::new\(\),/clipboard_context: {\n                #[cfg(all(target_os = "linux", target_env = "uclibc"))]\n                {\n                    Err(Box::new(io::Error::new(\n                        io::ErrorKind::Unsupported,\n                        "Clipboard support is unavailable on this target",\n                    )))\n                }\n                #[cfg(not(all(target_os = "linux", target_env = "uclibc")))]\n                {\n                    ClipboardProvider::new()\n                }\n            },/' src/app.rs; \
	fi; \
	$(JLESS_CARGO_BUILD_CMD) --target "$(JLESS_RUST_TARGET_ARG)" --bin jless

$(eval $(call INSTALL_BINARY_STRIP_RULE,$($(PKG)_BINARY),/usr/bin))

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(JLESS_DIR) clean
	$(RM) $($(PKG)_BINARY) $(JLESS_DIR)/.configured $(JLESS_DIR)/.cargo/config.toml

$(pkg)-uninstall:
	$(RM) $($(PKG)_TARGET_BINARY)

$(PKG_FINISH)
