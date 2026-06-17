$(call PKG_INIT_BIN, 1.9.7)
$(PKG)_SOURCE_DOWNLOAD_NAME:=dnsdist-$($(PKG)_VERSION).tar.bz2
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.bz2
$(PKG)_HASH:=285111c2b7dff6bc8a2407106a51c365cc5bf5e6287fe459a29b396c74620332
$(PKG)_SITE:=https://downloads.powerdns.com/releases
$(PKG)_DIR:=$(SOURCE_DIR)/dnsdist-$($(PKG)_VERSION)
### WEBSITE:=https://dnsdist.org/
### MANPAGE:=https://www.dnsdist.org/
### CHANGES:=https://www.dnsdist.org/changelog.html
### CVSREPO:=https://github.com/PowerDNS/pdns

# Keep the historical DNSDIST_* variable names after renaming the
# package path to pdns-dnsdist.
DNSDIST_DIR:=$(PDNS_DNSDIST_DIR)
DNSDIST_DEST_DIR:=$(PDNS_DNSDIST_DEST_DIR)
DNSDIST_CONFIGURE_PRE_CMDS = $(PDNS_DNSDIST_CONFIGURE_PRE_CMDS)
DNSDIST_CONFIGURE_ENV = $(PDNS_DNSDIST_CONFIGURE_ENV)
DNSDIST_CONFIGURE_OPTIONS = $(PDNS_DNSDIST_CONFIGURE_OPTIONS)

DNSDIST_BOOST_VERSION:=1.87.0
DNSDIST_BOOST_SOURCE:=dnsdist-boost_1_87_0.tar.bz2
DNSDIST_BOOST_SOURCE_DOWNLOAD_NAME:=boost_1_87_0.tar.bz2
DNSDIST_BOOST_HASH:=af57be25cb4c4f4b413ed692fe378affb4352ea50fbe294a11ef548f4d527d89
DNSDIST_BOOST_SITE:=https://archives.boost.io/release/$(DNSDIST_BOOST_VERSION)/source
DNSDIST_BOOST_ROOT:=$(DNSDIST_DIR)/.boost/boost_1_87_0
DNSDIST_BOOST_CONFIG:=$(DNSDIST_BOOST_ROOT)/user-config.jam
DNSDIST_BOOST_LIBDIR:=$(DNSDIST_BOOST_ROOT)/stage/lib
DNSDIST_BOOST_MARKER:=$(DNSDIST_BOOST_ROOT)/.built
DNSDIST_TOOLCHAIN_ERROR:=dnsdist 1.9.7 requires GCC 8+ with C++17 support.

DNSDIST_BUILD_BINARY:=$(DNSDIST_DIR)/dnsdist
DNSDIST_INSTALL_MARKER:=$(DNSDIST_DIR)/.installed

$(PKG)_DEPENDS_ON += $(STDCXXLIB)
$(PKG)_DEPENDS_ON += openssl lua
$(PKG)_DEPENDS_ON += $(if $(FREETZ_TARGET_ARCH_MIPS),$(if $(FREETZ_TARGET_GCC_4_8_MIN),libatomic))

$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_PDNS_DNSDIST_BINARY

$(PKG)_CONFIGURE_PRE_CMDS += $(call PKG_PREVENT_RPATH_HARDCODING,./configure)
# Keep the y2k38 workaround on generated configure to avoid autoreconf toolchain requirements.
$(PKG)_CONFIGURE_PRE_CMDS += sed -i '/as_fn_error.*y2k38/d' configure ;
# Fix upstream bug: PDNS_WITH_LIBEDIT uses $enableval instead of $withval,
# causing --with-libedit=no to be overwritten by stale $enableval value.
$(PKG)_CONFIGURE_PRE_CMDS += sed -i 's/with_libedit=$$enableval/with_libedit=$$withval/' configure ;

$(PKG)_CONFIGURE_ENV += BOOST_ROOT="$(abspath $(DNSDIST_BOOST_ROOT))"
$(PKG)_CONFIGURE_ENV += BOOST_INCLUDEDIR="$(abspath $(DNSDIST_BOOST_ROOT))"
$(PKG)_CONFIGURE_ENV += BOOST_LIBRARYDIR="$(abspath $(DNSDIST_BOOST_LIBDIR))"
$(PKG)_CONFIGURE_ENV += CPPFLAGS="-I$(abspath $(DNSDIST_BOOST_ROOT))"
$(PKG)_CONFIGURE_ENV += LDFLAGS="$(TARGET_LDFLAGS) -L$(abspath $(DNSDIST_BOOST_LIBDIR))"

$(PKG)_CONFIGURE_OPTIONS += --disable-silent-rules
$(PKG)_CONFIGURE_OPTIONS += --with-boost=$(abspath $(DNSDIST_BOOST_ROOT))
$(PKG)_CONFIGURE_OPTIONS += --with-lua=lua
$(PKG)_CONFIGURE_OPTIONS += --with-libcrypto=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr
$(PKG)_CONFIGURE_OPTIONS += --with-libssl=yes
$(PKG)_CONFIGURE_OPTIONS += --with-gnutls=no
$(PKG)_CONFIGURE_OPTIONS += --with-libsodium=no
$(PKG)_CONFIGURE_OPTIONS += --with-libedit=no
$(PKG)_CONFIGURE_OPTIONS += --with-libcap=no
$(PKG)_CONFIGURE_OPTIONS += --with-net-snmp=no
$(PKG)_CONFIGURE_OPTIONS += --with-re2=no
$(PKG)_CONFIGURE_OPTIONS += --with-ebpf=no
$(PKG)_CONFIGURE_OPTIONS += --with-xsk=no
$(PKG)_CONFIGURE_OPTIONS += --with-nghttp2=no
$(PKG)_CONFIGURE_OPTIONS += --with-h2o=no
$(PKG)_CONFIGURE_OPTIONS += --with-quiche=no
$(PKG)_CONFIGURE_OPTIONS += --with-lmdb=no
$(PKG)_CONFIGURE_OPTIONS += --with-cdb=no
$(PKG)_CONFIGURE_OPTIONS += --disable-dnstap
$(PKG)_CONFIGURE_OPTIONS += --disable-dnscrypt
$(PKG)_CONFIGURE_OPTIONS += --disable-tls-providers
$(PKG)_CONFIGURE_OPTIONS += --disable-dns-over-tls
$(PKG)_CONFIGURE_OPTIONS += --disable-dns-over-https
$(PKG)_CONFIGURE_OPTIONS += --disable-dns-over-quic
$(PKG)_CONFIGURE_OPTIONS += --disable-dns-over-http3
$(PKG)_CONFIGURE_OPTIONS += --disable-systemd

$(PKG)_EXCLUDED += $(if $(FREETZ_PACKAGE_PDNS_DNSDIST_BINARY),,usr/bin/dnsdist)

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)

$(DL_DIR)/$(DNSDIST_BOOST_SOURCE): | $(DL_DIR)
	$(DL_TOOL) -o $(DNSDIST_BOOST_SOURCE) $(DL_DIR) $(DNSDIST_BOOST_SOURCE_DOWNLOAD_NAME) $(DNSDIST_BOOST_SITE) $(DNSDIST_BOOST_HASH)

$(DNSDIST_BOOST_MARKER): $(DL_DIR)/$(DNSDIST_BOOST_SOURCE) $(DNSDIST_DIR)/.unpacked
	$(RM) -r $(DNSDIST_DIR)/.boost
	mkdir -p $(DNSDIST_DIR)/.boost
	$(call UNPACK_TARBALL,$<,$(DNSDIST_DIR)/.boost)
	cd $(DNSDIST_BOOST_ROOT) && ./bootstrap.sh --with-libraries=program_options,serialization,context,filesystem,system $(SILENT)
	printf "using gcc : : $(TARGET_CXX) : <archiver>$(TARGET_AR) <ranlib>$(TARGET_RANLIB) <compileflags>\"$(TARGET_CFLAGS) -fPIC\" <linkflags>\"$(TARGET_LDFLAGS)\" ;\n" > $(DNSDIST_BOOST_CONFIG)
	cd $(DNSDIST_BOOST_ROOT) && ./b2 --user-config=$(abspath $(DNSDIST_BOOST_CONFIG)) toolset=gcc $(subst ",,$(FREETZ_TARGET_B2_ARCH_OPTS)) target-os=linux link=static runtime-link=shared variant=release threading=multi cxxstd=17 --layout=system stage $(SILENT)
	@touch $@

$(DNSDIST_DIR)/.configured: $(DNSDIST_DIR)/.build-prereq-checked $(DNSDIST_DIR)/.unpacked $(if $(FREETZ_TARGET_GCC_8_MIN),$(DNSDIST_BOOST_MARKER))
	@$(call _ECHO,configuring)
	@if [ "$(FREETZ_TARGET_GCC_8_MIN)" != "y" ]; then \
		echo "ERROR: $(DNSDIST_TOOLCHAIN_ERROR)" 1>&2; \
		exit 1; \
	fi
	(cd $(DNSDIST_DIR) && \
		$(TARGET_CONFIGURE_PRE_CMDS) \
		$(DNSDIST_CONFIGURE_PRE_CMDS) \
		$(TARGET_CONFIGURE_ENV) $(DNSDIST_CONFIGURE_ENV) \
		./configure $(QUIET) $(TARGET_CONFIGURE_OPTIONS) $(DNSDIST_CONFIGURE_OPTIONS) $(SILENT) \
	) || { $(call ERROR,1,$(BUILD_FAIL_MSG)) }
	@touch $@

$(DNSDIST_BUILD_BINARY): $(DNSDIST_DIR)/.configured
	$(SUBMAKE) -C $(DNSDIST_DIR)

$(DNSDIST_INSTALL_MARKER): $(DNSDIST_BUILD_BINARY)
	$(SUBMAKE) -C $(DNSDIST_DIR) DESTDIR="$(abspath $(DNSDIST_DEST_DIR))" install
	$(RM) -r \
		$(DNSDIST_DEST_DIR)/usr/include \
		$(DNSDIST_DEST_DIR)/usr/share/doc \
		$(DNSDIST_DEST_DIR)/usr/share/man \
		$(DNSDIST_DEST_DIR)/usr/lib/pkgconfig
	$(TARGET_STRIP) $(DNSDIST_DEST_DIR)/usr/bin/dnsdist 2>/dev/null || true
	@touch $@

$(pkg):

$(pkg)-precompiled: $(DNSDIST_INSTALL_MARKER)

$(pkg)-clean:
	@if [ -f "$(DNSDIST_DIR)/Makefile" ]; then \
		$(SUBMAKE) -C $(DNSDIST_DIR) clean; \
	fi
	$(RM) -r $(DNSDIST_DIR)/.boost $(DNSDIST_DIR)/.configured $(DNSDIST_DIR)/.installed

$(pkg)-uninstall:
	$(RM) -r \
		$(DNSDIST_DEST_DIR)/usr/bin/dnsdist \
		$(DNSDIST_DEST_DIR)/etc/dnsdist.conf-dist

$(PKG_FINISH)
