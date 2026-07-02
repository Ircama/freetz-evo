$(call PKG_INIT_BIN, 1.1.1)
$(PKG)_SOURCE_DOWNLOAD_NAME:=v1.1.1.tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=cf3570c396ba36987059729f2704a88b87e4f154914062cf390b038694496be9
$(PKG)_SITE:=https://github.com/veeso/termscp/archive/refs/tags
$(PKG)_DIR:=$(SOURCE_DIR)/termscp-1.1.1
### WEBSITE:=https://github.com/veeso/termscp
### CHANGES:=https://github.com/veeso/termscp/releases
### CVSREPO:=https://github.com/veeso/termscp

include $(MAKE_DIR)/include/650-rust-cargo.mk

TERMSCP_RUST_TARGET_DIR:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(basename $(notdir $(RUST_TARGET_CUSTOM_NAME))))
TERMSCP_RUST_TARGET_ARG:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_SPEC_FILE))
TERMSCP_RUST_ENV_TARGET:=$(subst -,_,$(TERMSCP_RUST_TARGET_DIR))
TERMSCP_CARGO_BUILD_STD_FLAGS:=-Z build-std=std\,panic_abort
TERMSCP_CARGO_BUILD_CMD:=$(if $(RUST_TARGET_NEEDS_STD_BUILD),cargo +nightly build --release $(TERMSCP_CARGO_BUILD_STD_FLAGS),cargo build --release)
TERMSCP_CARGO_HOME:=$(abspath $(TERMSCP_DIR)/.cargo)
$(PKG)_BINARY:=$(TERMSCP_DIR)/target/$(TERMSCP_RUST_TARGET_DIR)/release/termscp
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/termscp

$(PKG)_DEPENDS_ON += rust-host
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_BUILTIN_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_CUSTOM_TARGET

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

# Fix termscp source: Parser<CB> doesn't have set_scrollback, use screen_mut().set_scrollback()
$(PKG)_PATCH_POST_CMDS += sed -i 's/self\.parser\.set_scrollback(/self.parser.screen_mut().set_scrollback(/g' $(TERMSCP_DIR)/src/ui/activities/filetransfer/components/terminal/component.rs;

$($(PKG)_BINARY): $(TERMSCP_DIR)/.configured
	cd $(abspath $(TERMSCP_DIR)); \
	export PATH=$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH; \
	export HOME="$(abspath $(TERMSCP_DIR))"; \
	export CARGO_HOME="$(TERMSCP_CARGO_HOME)"; \
	export RUSTUP_HOME="$(HOME)/.rustup"; \
	export CC_$(TERMSCP_RUST_TARGET_DIR)="$(TARGET_CROSS)gcc"; \
	export CXX_$(TERMSCP_RUST_TARGET_DIR)="$(TARGET_CROSS)g++"; \
	export AR_$(TERMSCP_RUST_TARGET_DIR)="$(TARGET_CROSS)ar"; \
	export RANLIB_$(TERMSCP_RUST_TARGET_DIR)="$(TARGET_CROSS)ranlib"; \
	export CC_$(TERMSCP_RUST_ENV_TARGET)="$(TARGET_CROSS)gcc"; \
	export CXX_$(TERMSCP_RUST_ENV_TARGET)="$(TARGET_CROSS)g++"; \
	export AR_$(TERMSCP_RUST_ENV_TARGET)="$(TARGET_CROSS)ar"; \
	export RANLIB_$(TERMSCP_RUST_ENV_TARGET)="$(TARGET_CROSS)ranlib"; \
	export HOST_CC="cc"; \
	$(RUST_OPENSSL_CROSS_ENV__INT) \
	export RUSTFLAGS="-C link-arg=-Wl,-no-pie"; \
	mkdir -p "$$CARGO_HOME"; \
	# Remove SMB (libsmbclient) from default features - not available for MIPS cross-compilation ;\
	perl -i -pe 's/default = \["keyring", "smb"\]/default = ["keyring"]/' "$(abspath $(TERMSCP_DIR))/Cargo.toml"; \
	echo "Patched termscp Cargo.toml: removed smb from default features" >&2; \
	# Fetch all deps ;\
	cargo fetch --target "$(TERMSCP_RUST_TARGET_ARG)"; \
	# Apply source patches after fetch extracted everything ;\
	for socket2_src in $$HOME/.cargo/registry/src/*/socket2-0.6.3/src/socket.rs $$HOME/.cargo/registry/src/*/socket2-0.6.4/src/socket.rs; do \
		[ -f "$$socket2_src" ] || continue; \
		sed -i 's/libc::IPV6_TRANSPARENT/libc::IP_TRANSPARENT/g' "$$socket2_src"; \
		echo "Patched socket2: $$socket2_src" >&2; \
	done; \
	$(call RUSTIX_APPLY_UCLIBC_PATCHES_RAW_DEP__INT,1.1.4) \
	$(call RUSTIX_APPLY_UCLIBC_PATCHES_LINUX_KERNEL__INT,0.38.44) \
	$(call GETRANDOM_APPLY_UCLIBC_MIPS_SYSCALL_PATCH__INT,0.3.4) \
	$(call GETRANDOM_APPLY_UCLIBC_MIPS_SYSCALL_PATCH__INT,0.4.2) \
	# Patch russh-sftp to replace AtomicU64 with AtomicU32 (not available on MIPS uClibc);\
	for russh_sftp_src in $$HOME/.cargo/registry/src/*/russh-sftp-*/src/client/rawsession.rs; do \
		[ -f "$$russh_sftp_src" ] || continue; \
		chmod u+w "$$russh_sftp_src"; \
		python3 -c "import re,sys;c=open(sys.argv[1]).read();c=c.replace('atomic::{AtomicU32, AtomicU64, Ordering}','atomic::{AtomicU32, Ordering}');c=c.replace('AtomicU64','AtomicU32');c=re.sub(r'\.store\(([a-zA-Z_][a-zA-Z_0-9.]+), Ordering::(\w+)\)',r'.store(\1 as u32, Ordering::\2)',c);c=re.sub(r'(self\.(?:handles|timeout))\.load\((Ordering::\w+)\)',r'u64::from(\1.load(\2))',c);c=re.sub(r'AtomicU32::new\(([a-zA-Z_][a-zA-Z_0-9.]+)\)',r'AtomicU32::new(\1 as u32)',c);open(sys.argv[1],'w').write(c);print('Patched russh-sftp')" "$$russh_sftp_src"; \
	done; \
	# Patch nucleo to replace AtomicU64 with AtomicUsize (not available on MIPS uClibc);\
	for nucleo_src in $$HOME/.cargo/registry/src/*/nucleo-*/src/boxcar.rs; do \
		[ -f "$$nucleo_src" ] || continue; \
		chmod u+w "$$nucleo_src"; \
		python3 -c "import re,sys;f=sys.argv[1];c=open(f).read();c=c.replace('atomic::{AtomicBool, AtomicPtr, AtomicU64, Ordering}','atomic::{AtomicBool, AtomicPtr, AtomicU32, Ordering}');c=c.replace('AtomicU64','AtomicU32');c=re.sub(r'((?:self\.(?:vec\.)?)inflight)\.load\(Ordering::(\w+)\)',r'u64::from(\1.load(Ordering::\2))',c);c=re.sub(r'\.min\(MAX_ENTRIES as u64\) as u32',r'.min(MAX_ENTRIES as u32)',c);open(f,'w').write(c);print('Patched nucleo')" "$$nucleo_src"; \
	done; \
	printf '[target.%s]\nlinker = "%s"\nar = "%s"\nrustflags = ["-C", "link-arg=-Wl,-no-pie"]\n' \
		"$(TERMSCP_RUST_TARGET_DIR)" \
		"$(TARGET_CROSS)gcc" \
		"$(TARGET_CROSS)ar" \
		> "$$CARGO_HOME/config.toml"; \
	echo "CARGO_HOME=$$CARGO_HOME" >&2; \
	cat "$$CARGO_HOME/config.toml" >&2; \
	# Patch openssl-src to recognize armv7-unknown-linux-uclibceabi -> linux-armv4 ;\
	$(OPENSSL_SRC_APPLY_UCLIBC_ARM_PATCH__INT) \
	$(TERMSCP_CARGO_BUILD_CMD) --target "$(TERMSCP_RUST_TARGET_ARG)" --bin termscp

$(eval $(call INSTALL_BINARY_STRIP_RULE,$($(PKG)_BINARY),/usr/bin))

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(TERMSCP_DIR) clean
	$(RM) -r $(TERMSCP_DIR)/target/release/build
	$(RM) $($(PKG)_BINARY) $(TERMSCP_DIR)/.unpacked $(TERMSCP_DIR)/.configured $(TERMSCP_DIR)/.cargo/config.toml

$(pkg)-uninstall:
	$(RM) $($(PKG)_TARGET_BINARY)

$(PKG_FINISH)
