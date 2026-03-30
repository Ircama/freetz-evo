$(call PKG_INIT_BIN, 18.20.8)
$(PKG)_SOURCE:=node-v$($(PKG)_VERSION).tar.xz
$(PKG)_HASH:=36a7bf1a76d62ce4badd881ee5974a323c70e1d8d19165732684e145632460d9
$(PKG)_SITE:=https://nodejs.org/dist/v$($(PKG)_VERSION)
### WEBSITE:=https://nodejs.org/
### MANPAGE:=https://nodejs.org/docs/latest/api/
### CHANGES:=https://github.com/nodejs/node/releases
### CVSREPO:=https://github.com/nodejs/node

$(PKG)_BINARY_BUILD:=$($(PKG)_DIR)/out/Release/node
$(PKG)_BINARY_TARGET:=$($(PKG)_DEST_DIR)/usr/bin/node

$(PKG)_DEPENDS_ON += python3-host openssl zlib libatomic $(STDCXXLIB)

$(PKG)_REBUILD_SUBOPTS += FREETZ_OPENSSL_SHORT_VERSION
$(PKG)_REBUILD_SUBOPTS += FREETZ_STDCXXLIB
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_ARCH_ENDIANNESS_DEPENDENT
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_ARCH_MIPS
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_ARCH_ARM
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_ARCH_AARCH64
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_ARCH_X86
$(PKG)_REBUILD_SUBOPTS += FREETZ_GCC_FLOAT_ABI
$(PKG)_REBUILD_SUBOPTS += FREETZ_GCC_FPU
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_NODEJS_WITH_NPM
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_NODEJS_WITH_INTL
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_NODEJS_WITH_INSPECTOR

NODEJS_HOST_MULTILIB_DIR := $(abspath ./build/host-multilib)
NODEJS_HOST_MULTILIB_CXXINC := $(NODEJS_HOST_MULTILIB_DIR)/usr/include/x86_64-linux-gnu/c++/13/32
NODEJS_HOST_MULTILIB_LIBDIR := $(NODEJS_HOST_MULTILIB_DIR)/usr/lib/gcc/x86_64-linux-gnu/13/32
NODEJS_USE_HOST_MULTILIB := $(if $(FREETZ_TARGET_ARCH_MIPS),y,)
NODEJS_HOST_CXXFLAGS := $(if $(NODEJS_USE_HOST_MULTILIB),-I$(NODEJS_HOST_MULTILIB_CXXINC),)
NODEJS_HOST_CPPFLAGS := $(NODEJS_HOST_CXXFLAGS)
NODEJS_HOST_LDFLAGS := $(if $(NODEJS_USE_HOST_MULTILIB),-L$(NODEJS_HOST_MULTILIB_LIBDIR),)

# Keep a single multiarch package recipe: map current Freetz target to Node.js dest-cpu.
$(PKG)_DEST_CPU := $(or \
	$(if $(FREETZ_TARGET_ARCH_AARCH64),arm64), \
	$(if $(FREETZ_TARGET_ARCH_ARM),arm), \
	$(if $(FREETZ_TARGET_ARCH_MIPS),$(if $(FREETZ_TARGET_ARCH_LE),mipsel,mips)), \
	$(if $(FREETZ_TARGET_ARCH_X86),ia32) \
)

# Fail early on unsupported architecture mapping when package is selected or nodejs goals are requested directly.
ifneq ($(strip $(FREETZ_PACKAGE_NODEJS)$(filter nodejs%,$(MAKECMDGOALS))),)
ifeq ($(strip $(NODEJS_DEST_CPU)),)
$(error nodejs: unsupported target architecture)
endif
endif

$(PKG)_CONFIGURE_DEFOPTS:=n

# V8/Node can emit 64-bit atomic ops on 32-bit Linux targets; ensure -latomic is linked.
$(PKG)_CONFIGURE_PRE_CMDS += $(SED) -i -e 's/OS=="linux" and clang==1/OS=="linux"/' node.gyp;

$(PKG)_CONFIGURE_ENV += PYTHON=$(HOST_TOOLS_DIR)/usr/bin/python3
# Ensure /usr/bin/env python3 resolves to host Python, not the target-toolchain wrapper.
$(PKG)_CONFIGURE_ENV += PATH="$(HOST_TOOLS_DIR)/usr/bin:$$$$PATH"
# Build host-side helper binaries with native compilers so they are executable during cross builds.
$(PKG)_CONFIGURE_ENV += CC_host="$(HOSTCC)"
$(PKG)_CONFIGURE_ENV += CXX_host="g++"
$(PKG)_CONFIGURE_ENV += LINK_host="g++"
$(PKG)_CONFIGURE_ENV += CFLAGS_host=""
$(PKG)_CONFIGURE_ENV += CXXFLAGS_host=""
$(PKG)_CONFIGURE_ENV += CPPFLAGS_host=""
$(PKG)_CONFIGURE_ENV += LDFLAGS_host=""

$(PKG)_CONFIGURE_OPTIONS += --prefix=/usr
$(PKG)_CONFIGURE_OPTIONS += --dest-os=linux
$(PKG)_CONFIGURE_OPTIONS += --dest-cpu=$(NODEJS_DEST_CPU)
$(PKG)_CONFIGURE_OPTIONS += --cross-compiling

$(PKG)_CONFIGURE_OPTIONS += --shared-openssl
$(PKG)_CONFIGURE_OPTIONS += --shared-zlib

$(PKG)_CONFIGURE_OPTIONS += $(if $(FREETZ_PACKAGE_NODEJS_WITH_NPM),,--without-npm)
$(PKG)_CONFIGURE_OPTIONS += $(if $(FREETZ_PACKAGE_NODEJS_WITH_INTL),--with-intl=small-icu,--without-intl)
$(PKG)_CONFIGURE_OPTIONS += $(if $(FREETZ_PACKAGE_NODEJS_WITH_INSPECTOR),,--without-inspector)

$(PKG)_CONFIGURE_OPTIONS += $(if $(FREETZ_TARGET_ARCH_ARM),--with-arm-float-abi=$(FREETZ_GCC_FLOAT_ABI))
$(PKG)_CONFIGURE_OPTIONS += $(if $(and $(FREETZ_TARGET_ARCH_ARM),$(FREETZ_GCC_FPU)),--with-arm-fpu=$(FREETZ_GCC_FPU))
$(PKG)_CONFIGURE_OPTIONS += $(if $(FREETZ_TARGET_ARCH_MIPS),--with-mips-float-abi=$(FREETZ_GCC_FLOAT_ABI))


$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_BINARY_BUILD): $($(PKG)_DIR)/.configured
	# Keep parallelism controlled by top-level make/jobserver.
	# Remove target sysroot paths from host-tool makefiles so host tools use host headers/libs.
	# Some host-only V8 helpers do not require OpenSSL; strip -lcrypto/-lssl from host makefiles
	# to avoid unnecessary host-link dependencies while keeping generated host flags untouched.
	find $(NODEJS_DIR)/out -type f -name '*.host.mk' -exec \
		sed -i \
			-e 's|-I$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include||g' \
			-e 's|-L$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib||g' \
			-e 's|-lcrypto||g' \
			-e 's|-lssl||g' {} +

ifneq ($(strip $(FREETZ_TARGET_ARCH_MIPS)),)
	# V8 in Node 18 still has an old MIPS cross-check that rejects x64 hosts for MIPS targets.
	# Relax this guard in the unpacked source for cross-builds on modern x64 hosts.
	$(SED) -i -e 's#(V8_TARGET_ARCH_MIPS && !(V8_HOST_ARCH_IA32 || V8_HOST_ARCH_MIPS))#(V8_TARGET_ARCH_MIPS \&\& !(V8_HOST_ARCH_IA32 || V8_HOST_ARCH_MIPS || V8_HOST_ARCH_X64))#' $(NODEJS_DIR)/deps/v8/src/base/build_config.h
	# Allow host-x64/target-mips cross builds through the tagged-size consistency check.
	grep -q 'V8_HOST_ARCH_X64' $(NODEJS_DIR)/deps/v8/src/common/globals.h || \
		$(SED) -i \
			-e '/STATIC_ASSERT((kTaggedSize == 8) == TAGGED_SIZE_8_BYTES);/c\
#if !(V8_TARGET_ARCH_MIPS && V8_HOST_ARCH_X64)\
STATIC_ASSERT((kTaggedSize == 8) == TAGGED_SIZE_8_BYTES);\
#endif' \
			$(NODEJS_DIR)/deps/v8/src/common/globals.h
	# GCC 13 + uClibc can require an explicit stdarg include for va_list in V8 base strings.
	grep -q '^#include <stdarg.h>' $(NODEJS_DIR)/deps/v8/src/base/strings.h || \
		$(SED) -i -e '/^#define V8_BASE_STRINGS_H_$$/a\
#include <stdarg.h>' $(NODEJS_DIR)/deps/v8/src/base/strings.h
	# On soft-float MIPS toolchains, V8's fp64 probe uses FPU registers and fails to compile.
	# Patch the probe to return fp32 mode immediately when __mips_soft_float is defined.
	grep -q '__mips_soft_float' $(NODEJS_DIR)/deps/v8/src/base/cpu.cc || \
		$(SED) -i \
			-e '/int __detect_fp64_mode(void) {/a\
#if defined(__mips_soft_float)\
  return 0;\
#else' \
			-e '/return !(result == 1);/a\
#endif' \
			$(NODEJS_DIR)/deps/v8/src/base/cpu.cc
	# GCC 13 can treat Operand(int64_t) as ambiguous here; use explicit int32 zero.
	$(SED) -i -e 's|Operand(static_cast<int64_t>(0))|Operand(static_cast<int32_t>(0))|g' \
		$(NODEJS_DIR)/deps/v8/src/compiler/backend/mips/code-generator-mips.cc
	# Soft-float MIPS has no FPU opcodes; skip mtc1-based register clobber asm.
	$(SED) -i \
		-e 's|#elif V8_HOST_ARCH_MIPS && V8_TARGET_ARCH_MIPS|#elif V8_HOST_ARCH_MIPS \&\& V8_TARGET_ARCH_MIPS \&\& !defined(__mips_soft_float)|' \
		$(NODEJS_DIR)/deps/v8/src/execution/clobber-registers.cc
	# On current V8/Object representation this path uses value objects, not pointers.
	$(SED) -i \
		-e 's#return y->ptr() | (static_cast<ObjectPair>(x->ptr()) << 32);#return y.ptr() | (static_cast<ObjectPair>(x.ptr()) << 32);#' \
		$(NODEJS_DIR)/deps/v8/src/runtime/runtime-utils.h
	# Liftoff Move now takes ValueKind; older arch files still pass ValueType.
	$(SED) -i -e 's|Move(tmp, src, type.value_type());|Move(tmp, src, type.value_type().kind());|g' \
		$(NODEJS_DIR)/deps/v8/src/wasm/baseline/mips/liftoff-assembler-mips.h \
		$(NODEJS_DIR)/deps/v8/src/wasm/baseline/mips64/liftoff-assembler-mips64.h \
		$(NODEJS_DIR)/deps/v8/src/wasm/baseline/riscv64/liftoff-assembler-riscv64.h
	# Host V8 makefiles are built with -m32; use ia32 stack-scan asm instead of x64.
	# The x64 variant uses %rbp/%r15 registers and fails under 32-bit assembler mode.
	find $(NODEJS_DIR)/out -type f -name '*.host.mk' -exec \
		sed -i \
			-e 's|/asm/x64/push_registers_asm|/asm/ia32/push_registers_asm|g' {} +

	# Host multilib is only needed for current MIPS host-tool build path (-m32 in *.host.mk).
	if [ ! -r "$(NODEJS_HOST_MULTILIB_CXXINC)/bits/c++config.h" ] || [ ! -r "$(NODEJS_HOST_MULTILIB_LIBDIR)/libstdc++.a" ]; then \
		echo "nodejs: missing local host multilib files under $(NODEJS_HOST_MULTILIB_DIR)" >&2; \
		echo "nodejs: run 'apt download lib32stdc++-13-dev && dpkg-deb -x lib32stdc++-13-dev_*.deb build/host-multilib'" >&2; \
		exit 1; \
	fi
endif

	$(SUBMAKE) -C $(NODEJS_DIR) \
		PATH="$(HOST_TOOLS_DIR)/usr/bin:$(PATH)" \
		CC.host="$(HOSTCC)" CXX.host="g++" LINK.host="g++" \
		CFLAGS.host="" \
		CXXFLAGS.host="$(NODEJS_HOST_CXXFLAGS)" \
		CPPFLAGS.host="$(NODEJS_HOST_CPPFLAGS)" \
		LDFLAGS.host="$(NODEJS_HOST_LDFLAGS)"


$($(PKG)_BINARY_TARGET): $($(PKG)_BINARY_BUILD)
	$(INSTALL_BINARY_STRIP)

$(pkg):

$(pkg)-precompiled: $($(PKG)_BINARY_TARGET)


$(pkg)-clean:
	-$(SUBMAKE) -C $(NODEJS_DIR) clean
	$(RM) $(NODEJS_DIR)/.configured

$(pkg)-uninstall:
	$(RM) $(NODEJS_BINARY_TARGET)

$(PKG_FINISH)
