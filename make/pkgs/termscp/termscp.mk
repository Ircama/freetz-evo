$(call PKG_INIT_BIN, 1.0.0)
$(PKG)_SOURCE_DOWNLOAD_NAME:=v1.0.0.tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=c07e2b82cb1cc327d977548e24d27fbbda8ee0cc4f2c3df9fb1b90c6e971e568
$(PKG)_SITE:=https://github.com/veeso/termscp/archive/refs/tags
$(PKG)_DIR:=$(SOURCE_DIR)/termscp-v1.0.0
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

# After patches are applied, remove the stale Cargo.lock so cargo regenerates it
# (necessary because we removed the vergen-git2 build-dep via patch).
$(PKG)_PATCH_POST_CMDS += rm -f $(TERMSCP_DIR)/Cargo.lock

# Fix termscp source: Parser<CB> doesn't have set_scrollback, use screen_mut().set_scrollback()
$(PKG)_PATCH_POST_CMDS += sed -i 's/self\.parser\.set_scrollback(/self.parser.screen_mut().set_scrollback(/g' $(TERMSCP_DIR)/src/ui/activities/filetransfer/components/terminal/component.rs;

$($(PKG)_BINARY): $(TERMSCP_DIR)/.configured
	cd $(abspath $(TERMSCP_DIR)); \
	export PATH=$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH; \
	export HOME="$(abspath $(TERMSCP_DIR))"; \
	export CARGO_HOME="$(TERMSCP_CARGO_HOME)"; \
	export RUSTUP_HOME="$(HOME)/.rustup"; \
	export CC_$(TERMSCP_RUST_ENV_TARGET)="$(TARGET_CROSS)gcc"; \
	export CXX_$(TERMSCP_RUST_ENV_TARGET)="$(TARGET_CROSS)g++"; \
	export AR_$(TERMSCP_RUST_ENV_TARGET)="$(TARGET_CROSS)ar"; \
	export RANLIB_$(TERMSCP_RUST_ENV_TARGET)="$(TARGET_CROSS)ranlib"; \
	export HOST_CC="cc"; \
	export OPENSSL_NO_VENDOR=1; \
	export OPENSSL_DIR="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr"; \
	export OPENSSL_LIB_DIR="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib"; \
	export OPENSSL_INCLUDE_DIR="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include"; \
	export VERGEN_BUILD_TIMESTAMP="2026-06-14"; \
	export VERGEN_GIT_BRANCH="master"; \
	export VERGEN_GIT_SHA="freetz-build"; \
	mkdir -p "$$CARGO_HOME"; \
	# Fix termscp source: Parser<CB> doesn't have set_scrollback/set_size, use screen_mut() ;\
	sed -i 's/self\.parser\.set_scrollback(/self.parser.screen_mut().set_scrollback(/g' "$(abspath $(TERMSCP_DIR))/src/ui/activities/filetransfer/components/terminal/component.rs"; \
	sed -i 's/self\.parser\.set_size(/self.parser.screen_mut().set_size(/g' "$(abspath $(TERMSCP_DIR))/src/ui/activities/filetransfer/components/terminal/component.rs"; \
	# Remove SMB (libsmbclient) from default features - not available for MIPS cross-compilation ;\
	perl -i -pe 's/default = \["keyring", "smb"\]/default = ["keyring"]/' "$(abspath $(TERMSCP_DIR))/Cargo.toml"; \
	echo "Patched termscp Cargo.toml: removed smb from default features" >&2; \
	# Regenerate Cargo.lock FIRST (now without smb/remotefs-smb/pavao-sys/git2), so cargo fetch downloads everything ;\
	cd "$$HOME" && cargo generate-lockfile 2>/dev/null || true; \
	cd $(abspath $(TERMSCP_DIR)); \
	# Now fetch ALL deps (lockfile is up-to-date) ;\
	cargo fetch --target "$(TERMSCP_RUST_TARGET_ARG)"; \
	# NOW apply all source patches AFTER fetch extracted everything ;\
	for ssh2_cfg_src in $$HOME/.cargo/registry/src/*/ssh2-config-0.7.0/Cargo.toml $$HOME/.cargo/registry/src/*/ssh2-config-0.7.1/Cargo.toml; do \
		[ -f "$$ssh2_cfg_src" ] || continue; \
		chmod -R u+w "$$(dirname "$$ssh2_cfg_src")"; \
		perl -0pi -e 's/\n\[build-dependencies\.git2\]\nversion = "0\.20"/\n# git2 build-dep removed for host build compatibility\n# [build-dependencies.git2]\n# version = "0.20"/' "$$ssh2_cfg_src"; \
	done; \
	for ssh2_openssh_src in $$HOME/.cargo/registry/src/*/ssh2-config-0.7.0/build/openssh.rs $$HOME/.cargo/registry/src/*/ssh2-config-0.7.1/build/openssh.rs; do \
		[ -f "$$ssh2_openssh_src" ] || continue; \
		chmod -R u+w "$$(dirname "$$ssh2_openssh_src")"; \
		perl -0pi -e 's/fn clone_openssh\(path: \&Path\) -> anyhow::Result<\(\)> \{[^}]*\}/fn clone_openssh(path: \&Path) -> anyhow::Result<()> {\n    Err(anyhow::anyhow!("git2 not available: OpenSSH source cloning disabled"))\n}/' "$$ssh2_openssh_src"; \
	done; \
	for pavao_src_cfg in $$HOME/.cargo/registry/src/*/pavao-src-4.22.0-4/Cargo.toml; do \
		[ -f "$$pavao_src_cfg" ] || continue; \
		chmod u+w "$$pavao_src_cfg" "$$(dirname "$$pavao_src_cfg")"; \
		perl -0pi -e 's/\[dependencies\.git2\]\nversion = "0\.20"/# git2 removed for HOST build compatibility\n# [dependencies.git2]\n# version = "0.20"/' "$$pavao_src_cfg"; \
		echo "Patched pavao-src Cargo.toml (removed git2)" >&2; \
	done; \
	for socket2_src in $$HOME/.cargo/registry/src/*/socket2-0.6.3/src/socket.rs $$HOME/.cargo/registry/src/*/socket2-0.6.4/src/socket.rs; do \
		[ -f "$$socket2_src" ] || continue; \
		sed -i 's/libc::IPV6_TRANSPARENT/libc::IP_TRANSPARENT/g' "$$socket2_src"; \
		echo "Patched socket2: $$socket2_src" >&2; \
		grep -c 'IPV6_TRANSPARENT' "$$socket2_src" | xargs -I{} echo "  $$(basename $$(dirname $$(dirname $$socket2_src))): {} IPV6_TRANSPARENT remaining" >&2; \
	done; \
	$(call RUSTIX_APPLY_UCLIBC_PATCHES_RAW_DEP__INT,1.1.4) \
	$(call RUSTIX_APPLY_UCLIBC_PATCHES_LINUX_KERNEL__INT,0.38.44) \
	$(call GETRANDOM_APPLY_UCLIBC_MIPS_SYSCALL_PATCH__INT,0.3.4) \
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
	$(call GETRANDOM_APPLY_UCLIBC_MIPS_SYSCALL_PATCH__INT,0.4.2) \
	# Find the patched ssh2-config directory for [patch.crates-io] override ;\
	SSH2_CFG_DIR=$$(find "$$HOME/.cargo/registry/src" -maxdepth 2 -type d -name 'ssh2-config-0.7.*' | head -1); \
	echo "Using patched ssh2-config at: $$SSH2_CFG_DIR" >&2; \
	printf '[target.%s]\nlinker = "%s"\nar = "%s"\n' \
		"$(TERMSCP_RUST_TARGET_DIR)" \
		"$(TARGET_CROSS)gcc" \
		"$(TARGET_CROSS)ar" \
		> "$$CARGO_HOME/config.toml"; \
	printf '\n[env]\nOPENSSL_DIR = "%s"\nOPENSSL_LIB_DIR = "%s/lib"\nOPENSSL_INCLUDE_DIR = "%s/include"\n' \
		"$(TARGET_TOOLCHAIN_STAGING_DIR)/usr" \
		"$(TARGET_TOOLCHAIN_STAGING_DIR)/usr" \
		"$(TARGET_TOOLCHAIN_STAGING_DIR)/usr" \
		>> "$$CARGO_HOME/config.toml"; \
	printf '\n[patch.crates-io]\nssh2-config = { path = "%s" }\n' \
		"$$SSH2_CFG_DIR" \
		>> "$$CARGO_HOME/config.toml"; \
	echo "CARGO_HOME=$$CARGO_HOME" >&2; \
	cat "$$CARGO_HOME/config.toml" >&2; \
	# Delete stale lockfile and regenerate with [patch] in effect (resolves without git2) ;\
	rm -f "$$HOME/Cargo.lock"; \
	cd "$$HOME" && cargo generate-lockfile 2>/dev/null || true; \
	cd $(abspath $(TERMSCP_DIR)); \
	$(TERMSCP_CARGO_BUILD_CMD) --target "$(TERMSCP_RUST_TARGET_ARG)" --bin termscp

$(eval $(call INSTALL_BINARY_STRIP_RULE,$($(PKG)_BINARY),/usr/bin))

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(TERMSCP_DIR) clean
	$(RM) $($(PKG)_BINARY) $(TERMSCP_DIR)/.unpacked $(TERMSCP_DIR)/.configured $(TERMSCP_DIR)/.cargo/config.toml

$(pkg)-uninstall:
	$(RM) $($(PKG)_TARGET_BINARY)

$(PKG_FINISH)
