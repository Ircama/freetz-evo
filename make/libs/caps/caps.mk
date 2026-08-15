$(call PKG_INIT_LIB, 0.9.26)
$(PKG)_SOURCE:=caps_$($(PKG)_VERSION).tar.bz2
$(PKG)_HASH:=e7496c5bce05abebe3dcb635926153bbb58a9337a6e423f048d3b61d8a4f98c9
$(PKG)_SITE:=https://quitte.de/dsp
### WEBSITE:=https://quitte.de/dsp/caps.html
### MANPAGE:=https://quitte.de/dsp/caps.html
### CHANGES:=https://quitte.de/dsp/caps.html
### PKGSITE:=https://github.com/Ircama/freetz-evo/tree/master/make/libs/caps/

# Patch 010-fix-exp10f-uclibc.patch (dsp/v4f_IIR2.h): uClibc (all versions,
# including uClibc-ng 1.0.58) does not declare exp10f in <math.h>, so the
# __APPLE__-only fallback in caps leaves 'exp10f was not declared' errors on
# uClibc toolchains. The patch provides exp10f via powf(10.0f, f) when
# __UCLIBC__ is defined. glibc is unaffected (native exp10f declaration).

$(PKG)_CATEGORY_LIBS:=Multimedia##Audio I/O
$(PKG)_BINARY:=$($(PKG)_DIR)/caps.so
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/ladspa/caps.so
$(PKG)_STAGING_RDF:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/share/ladspa/rdf/caps.rdf
# The real library deployed to the target (ladspa/caps.so).
$(PKG)_TARGET_LIB:=$($(PKG)_TARGET_DIR)/ladspa/caps.so
# Convenience symlink at the top of FREETZ_LIBRARY_DIR that LADSPA hosts
# expect (caps.so -> ladspa/caps.so).
$(PKG)_TARGET_SYMLINK:=$($(PKG)_TARGET_DIR)/caps.so

$(PKG)_DEPENDS_ON += $(STDCXXLIB)
$(PKG)_REBUILD_SUBOPTS += FREETZ_STDCXXLIB

CAPS_MAKE_ENV := \
	CC="$(TARGET_CXX)" \
	STRIP="$(TARGET_STRIP)" \
	PREFIX=/usr \
	DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
	ARCH= \
	_CFLAGS= \
	_LDFLAGS="-shared -lm"

CAPS_MAKE_OPTS := \
	OPTS="$(TARGET_CFLAGS) -O3 -ffast-math -funroll-loops -Wall -fPIC -DPIC"

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(CAPS_DIR) \
		$(CAPS_MAKE_ENV) \
		$(CAPS_MAKE_OPTS) \
		all

$($(PKG)_STAGING_BINARY): $($(PKG)_BINARY)
	$(SUBMAKE) -C $(CAPS_DIR) \
		$(CAPS_MAKE_ENV) \
		$(CAPS_MAKE_OPTS) \
		install

$($(PKG)_STAGING_RDF): $($(PKG)_STAGING_BINARY)
	[ -f "$@" ]

# Deploy the real library from staging to target packages directory.
# caps.so is a LADSPA plugin whose name does not follow the lib*.so*
# convention, so INSTALL_LIBRARY_STRIP cannot be used (the LIBRARY_NAME_TO_SHELL_PATTERN
# helper only matches names starting with "lib").  Use plain cp + strip instead.
$($(PKG)_TARGET_LIB): $($(PKG)_STAGING_BINARY)
	mkdir -p $(dir $@)
	cp -a $< $@
	$(TARGET_STRIP) $@

# Convenience symlink depending on the real file, so make only recreates
# the symlink when the underlying library has actually been updated.
$($(PKG)_TARGET_SYMLINK): $($(PKG)_TARGET_LIB)
	mkdir -p $(dir $@)
	$(RM) -f $@
	ln -s ladspa/caps.so $@

$(pkg): $($(PKG)_STAGING_BINARY) $($(PKG)_STAGING_RDF)

$(pkg)-precompiled: $($(PKG)_TARGET_LIB) $($(PKG)_TARGET_SYMLINK)

$(pkg)-clean:
	-$(SUBMAKE) -C $(CAPS_DIR) clean
	$(RM) -r \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/ladspa/caps.so \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/share/ladspa/rdf/caps.rdf \
		$(TARGET_SPECIFIC_ROOT_DIR)$(FREETZ_LIBRARY_DIR)/ladspa/caps.so \
		$(TARGET_SPECIFIC_ROOT_DIR)/usr/share/ladspa/rdf/caps.rdf

$(pkg)-uninstall:
	$(RM) -f \
		$(CAPS_TARGET_SYMLINK) \
		$(CAPS_TARGET_LIB) \
		$(TARGET_SPECIFIC_ROOT_DIR)/usr/share/ladspa/rdf/caps.rdf

$(PKG_FINISH)
