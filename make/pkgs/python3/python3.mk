$(call PKG_INIT_BIN, 3.14.3)
$(PKG)_SOURCE:=Python-$($(PKG)_VERSION).tar.xz
$(PKG)_HASH:=a97d5549e9ad81fe17159ed02c68774ad5d266c72f8d9a0b5a9c371fe85d902b
$(PKG)_SITE:=https://www.python.org/ftp/python/$($(PKG)_VERSION)
### WEBSITE:=https://www.python.org/
### MANPAGE:=https://docs.python.org/3/
### CHANGES:=https://www.python.org/downloads/
### CVSREPO:=https://github.com/python/cpython
### SUPPORT:=Ircama

$(PKG)_DEPENDS_ON+=patchelf-target-host

$(PKG)_LOCAL_INSTALL_DIR:=$($(PKG)_DIR)/_install

$(PKG)_MAJOR_VERSION:=$(call GET_MAJOR_VERSION,$($(PKG)_VERSION))
$(PKG)_MAJOR_VERSION_1:=$(call GET_MAJOR_VERSION,$($(PKG)_VERSION),1)

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/python$($(PKG)_MAJOR_VERSION).bin
$(PKG)_LIB_PYTHON3_TARGET_DIR:=$($(PKG)_TARGET_LIBDIR)/libpython$($(PKG)_MAJOR_VERSION).so.1.0
$(PKG)_ZIPPED_PYC:=usr/lib/python$(subst .,,$($(PKG)_MAJOR_VERSION)).zip
$(PKG)_ZIPPED_PYC_TARGET_DIR:=$($(PKG)_DEST_DIR)/$($(PKG)_ZIPPED_PYC)

$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin/python$($(PKG)_MAJOR_VERSION)

include $(MAKE_DIR)/pkgs/python3/python3-module-macros.mk.in

include $(MAKE_DIR)/pkgs/python3/python3-filelists.mk.in

$(PKG)_MODULES_ALL := \
	audiodev audioop bsddb cmath cprofile crypt csv ctypes curses \
	eastern_codecs elementtree ensurepip grp hotshot json \
	mmap multiprocessing readline spwd sqlite ssl \
	syslog termios test tkinter unicodedata unittest wsgiref
$(PKG)_MODULES_SELECTED := $(call PKG_SELECTED_SUBOPTIONS,$($(PKG)_MODULES_ALL),MOD)
$(PKG)_MODULES_EXCLUDED := $(filter-out $($(PKG)_MODULES_SELECTED),$($(PKG)_MODULES_ALL))

$(PKG)_EXCLUDED_FILES   := $(call newline2space,$(foreach mod,$($(PKG)_MODULES_EXCLUDED),$(PyMod3/$(mod)/files)))
$(PKG)_UNNECESSARY_DIRS := $(if $(FREETZ_PACKAGE_PYTHON3_COMPRESS_PYC),$(call newline2space,$(Python3/unnecessary-if-compression-enabled/dirs)))
$(PKG)_UNNECESSARY_DIRS += $(call newline2space,$(foreach mod,$($(PKG)_MODULES_EXCLUDED),$(PyMod3/$(mod)/dirs)))

$(PKG)_DEPENDS_ON += python3-host expat libffi zlib
$(PKG)_DEPENDS_ON += $(if $(FREETZ_SEPARATE_AVM_UCLIBC),patchelf-target-host)
$(PKG)_DEPENDS_ON += $(if $(FREETZ_PACKAGE_PYTHON3_MOD_BSDDB),db)
$(PKG)_DEPENDS_ON += $(if $(or $(FREETZ_PACKAGE_PYTHON3_MOD_CURSES),$(FREETZ_PACKAGE_PYTHON3_MOD_READLINE)),ncurses)
$(PKG)_DEPENDS_ON += $(if $(FREETZ_PACKAGE_PYTHON3_MOD_READLINE),readline)
$(PKG)_DEPENDS_ON += $(if $(FREETZ_PACKAGE_PYTHON3_MOD_SQLITE),sqlite)
$(PKG)_DEPENDS_ON += $(if $(FREETZ_PACKAGE_PYTHON3_MOD_SSL),openssl)
$(PKG)_DEPENDS_ON += $(if $(FREETZ_PACKAGE_PYTHON3_MOD_TKINTER),tcl tk libX11 libXt libXext)

$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_PYTHON3_STATIC
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_PYTHON3_MOD_BSDDB
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_PYTHON3_MOD_CURSES
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_PYTHON3_MOD_READLINE
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_PYTHON3_MOD_SQLITE
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_PYTHON3_MOD_SSL
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_PYTHON3_MOD_TKINTER
$(PKG)_REBUILD_SUBOPTS += $(OPENSSL_REBUILD_SUBOPTS)
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_IPV6_SUPPORT
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_PYTHON3_COMPILER_ONDEVICE

# Sysconfig compiler names: on-device GCC uses plain "gcc"/"g++",
# cross-compiler mode uses the prefixed toolchain basenames.
ifeq ($(strip $(FREETZ_PACKAGE_PYTHON3_COMPILER_ONDEVICE)),y)
PYTHON3_SYSCONFIG_CC     := gcc
PYTHON3_SYSCONFIG_CXX    := g++
PYTHON3_SYSCONFIG_AR     := ar
PYTHON3_SYSCONFIG_RANLIB := ranlib
else
PYTHON3_SYSCONFIG_CC     := $(notdir $(TARGET_CC))
PYTHON3_SYSCONFIG_CXX    := $(notdir $(TARGET_CXX))
PYTHON3_SYSCONFIG_AR     := $(notdir $(TARGET_AR))
PYTHON3_SYSCONFIG_RANLIB := $(notdir $(TARGET_RANLIB))
endif

$(PKG)_CONFIGURE_ENV += ac_cv_have_chflags=no
$(PKG)_CONFIGURE_ENV += ac_cv_have_lchflags=no
$(PKG)_CONFIGURE_ENV += ac_cv_py_format_size_t=no
$(PKG)_CONFIGURE_ENV += ac_cv_have_long_long_format=yes
$(PKG)_CONFIGURE_ENV += ac_cv_buggy_getaddrinfo=no
$(PKG)_CONFIGURE_ENV += ac_cv_file__dev_ptmx=no
$(PKG)_CONFIGURE_ENV += ac_cv_file__dev_ptc=no
$(PKG)_CONFIGURE_ENV += OPT="-fno-inline"

$(PKG)_CONFIGURE_OPTIONS += --disable-test-modules
$(PKG)_CONFIGURE_OPTIONS += --with-system-expat
$(PKG)_CONFIGURE_OPTIONS += --with-build-python=$(abspath $(TOOLS_DIR)/path/python3)
$(PKG)_CONFIGURE_OPTIONS += --with-ensurepip=no
$(PKG)_CONFIGURE_OPTIONS += --enable-ipv6
$(PKG)_CONFIGURE_OPTIONS += $(if $(FREETZ_PACKAGE_PYTHON3_STATIC),--disable-shared,--enable-shared)

$(PKG)_CONFIGURE_OPTIONS += $(if $(FREETZ_PACKAGE_PYTHON3_MOD_TKINTER),--with-tcltk-includes="-I$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include")
$(PKG)_CONFIGURE_OPTIONS += $(if $(FREETZ_PACKAGE_PYTHON3_MOD_TKINTER),--with-tcltk-libs="-L$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib -ltcl8.6 -ltk8.6")

# remove local copy of libffi, we use system one
$(PKG)_CONFIGURE_PRE_CMDS += $(RM) -r Modules/_ctypes/libffi*;
# remove local copy of expat, we use system one
$(PKG)_CONFIGURE_PRE_CMDS += $(RM) -r Modules/expat;
# remove local copy of zlib, we use system one
$(PKG)_CONFIGURE_PRE_CMDS += $(RM) -r Modules/zlib;

ifneq ($(strip $(DL_DIR)/$(PYTHON3_SOURCE)),$(strip $(DL_DIR)/$(PYTHON3_HOST_SOURCE)))
$(PKG_SOURCE_DOWNLOAD)
endif
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_DIR)/.compiled: $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(PYTHON3_DIR) \
		all
	touch $@

$($(PKG)_DIR)/.installed: $($(PKG)_DIR)/.compiled
	$(SUBMAKE) -C $(PYTHON3_DIR) \
		DESTDIR="$(FREETZ_BASE_DIR)/$(PYTHON3_LOCAL_INSTALL_DIR)" \
		install
	(cd $(FREETZ_BASE_DIR)/$(PYTHON3_LOCAL_INSTALL_DIR); \
		chmod -R u+w usr; \
		$(RM) -r $(call newline2space,$(Python3/unnecessary/files)); \
		\
		find usr/lib/python$(PYTHON3_MAJOR_VERSION)/ -name "*.pyo" -delete; \
		find usr/lib/python$(PYTHON3_MAJOR_VERSION)/ -type f -name "_sysconfigdata*.py" -exec \
			$(SED) -i -r \
				-e "s,'CC': '[^']*','CC': '$(PYTHON3_SYSCONFIG_CC)'," \
				-e "s,'CXX': '[^']*','CXX': '$(PYTHON3_SYSCONFIG_CXX)'," \
				-e "s,'LDSHARED': '[^']*','LDSHARED': '$(PYTHON3_SYSCONFIG_CC) -shared'," \
				-e "s,'BLDSHARED': '[^']*','BLDSHARED': '$(PYTHON3_SYSCONFIG_CC) -shared'," \
				-e "s,'LINKCC': '[^']*','LINKCC': '$(PYTHON3_SYSCONFIG_CC)'," \
				-e "s,'LDCXXSHARED': '[^']*','LDCXXSHARED': '$(PYTHON3_SYSCONFIG_CXX) -shared'," \
				-e "s,'AR': '[^']*','AR': '$(PYTHON3_SYSCONFIG_AR)'," \
				-e "s,'RANLIB': '[^']*','RANLIB': '$(PYTHON3_SYSCONFIG_RANLIB)'," \
			{} +; \
		find usr/lib/python$(PYTHON3_MAJOR_VERSION)/ -type f -name "_sysconfig_vars*.json" -exec \
			$(SED) -i -r \
				-e 's,"CC"[[:space:]]*:[[:space:]]*"[^"]*","CC": "$(PYTHON3_SYSCONFIG_CC)",' \
				-e 's,"CXX"[[:space:]]*:[[:space:]]*"[^"]*","CXX": "$(PYTHON3_SYSCONFIG_CXX)",' \
				-e 's,"LDSHARED"[[:space:]]*:[[:space:]]*"[^"]*","LDSHARED": "$(PYTHON3_SYSCONFIG_CC) -shared",' \
				-e 's,"BLDSHARED"[[:space:]]*:[[:space:]]*"[^"]*","BLDSHARED": "$(PYTHON3_SYSCONFIG_CC) -shared",' \
				-e 's,"LINKCC"[[:space:]]*:[[:space:]]*"[^"]*","LINKCC": "$(PYTHON3_SYSCONFIG_CC)",' \
				-e 's,"LDCXXSHARED"[[:space:]]*:[[:space:]]*"[^"]*","LDCXXSHARED": "$(PYTHON3_SYSCONFIG_CXX) -shared",' \
				-e 's,"AR"[[:space:]]*:[[:space:]]*"[^"]*","AR": "$(PYTHON3_SYSCONFIG_AR)",' \
				-e 's,"RANLIB"[[:space:]]*:[[:space:]]*"[^"]*","RANLIB": "$(PYTHON3_SYSCONFIG_RANLIB)",' \
			{} +; \
		find usr/lib/python$(PYTHON3_MAJOR_VERSION)/ -type f -path "*/config-$(PYTHON3_MAJOR_VERSION)/Makefile" -exec \
			$(SED) -i -r \
				-e "s,^CC[[:space:]]*=.*,CC=$(PYTHON3_SYSCONFIG_CC)," \
				-e "s,^CXX[[:space:]]*=.*,CXX=$(PYTHON3_SYSCONFIG_CXX)," \
				-e "s,^LDSHARED[[:space:]]*=.*,LDSHARED=$(PYTHON3_SYSCONFIG_CC) -shared," \
				-e "s,^BLDSHARED[[:space:]]*=.*,BLDSHARED=$(PYTHON3_SYSCONFIG_CC) -shared," \
				-e "s,^LINKCC[[:space:]]*=.*,LINKCC=$(PYTHON3_SYSCONFIG_CC)," \
				-e "s,^LDCXXSHARED[[:space:]]*=.*,LDCXXSHARED=$(PYTHON3_SYSCONFIG_CXX) -shared," \
				-e "s,^AR[[:space:]]*=.*,AR=$(PYTHON3_SYSCONFIG_AR)," \
				-e "s,^RANLIB[[:space:]]*=.*,RANLIB=$(PYTHON3_SYSCONFIG_RANLIB)," \
			{} +; \
		\
		find usr/lib/python$(PYTHON3_MAJOR_VERSION)/ -path "*/__pycache__/_sysconfigdata*" -name "*.pyc" -delete; \
		find usr/lib/python$(PYTHON3_MAJOR_VERSION)/ -type f -name "_sysconfigdata*.py" \
			-exec $(FREETZ_BASE_DIR)/$(TOOLS_DIR)/path/python3 -c \
				"import py_compile,sys; py_compile.compile(sys.argv[1])" {} \; ; \
		find usr/lib/python$(PYTHON3_MAJOR_VERSION)/ -type f -name "_sysconfigdata*.py" \
			-exec $(FREETZ_BASE_DIR)/$(TOOLS_DIR)/path/python3 -O -c \
				"import py_compile,sys; py_compile.compile(sys.argv[1])" {} \; ; \
		find usr/lib/python$(PYTHON3_MAJOR_VERSION)/ -type f -name "_sysconfigdata*.py" \
			-exec $(FREETZ_BASE_DIR)/$(TOOLS_DIR)/path/python3 -OO -c \
				"import py_compile,sys; py_compile.compile(sys.argv[1])" {} \; ; \
		\
		$(TARGET_STRIP) \
			usr/bin/python$(PYTHON3_MAJOR_VERSION) \
			$(if $(FREETZ_PACKAGE_PYTHON3_STATIC),,usr/lib/libpython$(PYTHON3_MAJOR_VERSION).so.1.0) \
			usr/lib/python$(PYTHON3_MAJOR_VERSION)/lib-dynload/*.so; \
		\
		mv usr/bin/python$(PYTHON3_MAJOR_VERSION) usr/bin/python$(PYTHON3_MAJOR_VERSION).bin; \
		\
		[ "$(FREETZ_SEPARATE_AVM_UCLIBC)" != "y" ] || $(FREETZ_BASE_DIR)/$(TOOLS_DIR)/patchelf-target --set-interpreter $(FREETZ_LIBRARY_DIR)/ld-uClibc.so.1 usr/bin/python$(PYTHON3_MAJOR_VERSION).bin; \
	)
	touch $@

$($(PKG)_STAGING_BINARY): $($(PKG)_DIR)/.installed
	@$(call COPY_USING_TAR,$(PYTHON3_LOCAL_INSTALL_DIR)/usr,$(TARGET_TOOLCHAIN_STAGING_DIR)/usr,--exclude='*.pyc' .) \
	$(PKG_FIX_LIBTOOL_LA) $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/python-$(PYTHON3_MAJOR_VERSION).pc; \
	ln -sf python$(PYTHON3_MAJOR_VERSION).bin $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin/python$(PYTHON3_MAJOR_VERSION)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.installed
	@$(call COPY_USING_TAR,$(PYTHON3_LOCAL_INSTALL_DIR),$(PYTHON3_DEST_DIR),--exclude='libpython$(PYTHON3_MAJOR_VERSION).so*' .) \
	(cd $(PYTHON3_DEST_DIR); \
		echo -n > usr/lib/python$(PYTHON3_MAJOR_VERSION)/config-$(PYTHON3_MAJOR_VERSION)/Makefile; \
		$(RM) -r $(call newline2space,$(Python3/development/files)); \
	)

ifneq ($(strip $(FREETZ_PACKAGE_PYTHON3_STATIC)),y)
$($(PKG)_LIB_PYTHON3_TARGET_DIR): $($(PKG)_DIR)/.installed
	@mkdir -p $(dir $@); \
	cp -a $(PYTHON3_LOCAL_INSTALL_DIR)/usr/lib/libpython$(PYTHON3_MAJOR_VERSION).so* $(dir $@)
endif

$(pkg): $($(PKG)_TARGET_DIR)/.exclude-extra

$($(PKG)_TARGET_DIR)/py.lst $($(PKG)_TARGET_DIR)/pyc.lst: $($(PKG)_DIR)/.installed $(PACKAGES_DIR)/.$(pkg)-$($(PKG)_VERSION)
	@(cd $(FREETZ_BASE_DIR)/$(PYTHON3_LOCAL_INSTALL_DIR); \
		find usr -type f -name "*.$(basename $(notdir $@))"  | sort > $(FREETZ_BASE_DIR)/$@; \
	)

$($(PKG)_TARGET_DIR)/excluded-module-files.lst: $(TOPDIR)/.config $(PACKAGES_DIR)/.$(pkg)-$($(PKG)_VERSION)
	@(tmp="$@.tmp"; set -f; echo $(PYTHON3_EXCLUDED_FILES) | tr " " "\n" | sort > "$$tmp"; \
		if ! cmp -s "$$tmp" "$@" 2>/dev/null; then mv "$$tmp" "$@"; else rm -f "$$tmp"; fi)

$($(PKG)_TARGET_DIR)/excluded-module-files-zip.lst: $($(PKG)_TARGET_DIR)/excluded-module-files.lst
	@(tmp="$@.tmp"; sed -r 's,usr/lib/python$(PYTHON3_MAJOR_VERSION)/,,g' $< > "$$tmp"; \
		if ! cmp -s "$$tmp" "$@" 2>/dev/null; then mv "$$tmp" "$@"; else rm -f "$$tmp"; fi)

# Python 3.14 zip importer fix: copy .pyc files from __pycache__ to package level
# This ensures compatibility with Python 3.14's zip importer which expects
# .pyc files to be available at both __pycache__ and package level

$($(PKG)_ZIPPED_PYC_TARGET_DIR): $($(PKG)_TARGET_DIR)/excluded-module-files-zip.lst $($(PKG)_TARGET_BINARY)
	@(cd $(dir $@)/python$(PYTHON3_MAJOR_VERSION); \
		$(RM) ../$(notdir $@); \
		$(if $(FREETZ_PACKAGE_PYTHON3_COMPRESS_PYC),zip -9qyR -x@$(FREETZ_BASE_DIR)/$(PYTHON3_TARGET_DIR)/excluded-module-files-zip.lst ../$(notdir $@) . "*.pyc";) \
	)
	$(if $(FREETZ_PACKAGE_PYTHON3_COMPRESS_PYC), \
		$(FREETZ_BASE_DIR)/make/pkgs/python3/scripts/fix-python314-zip.sh $(FREETZ_BASE_DIR)/$@ $(SILENT); \
	)

$($(PKG)_TARGET_DIR)/.exclude-extra: $(TOPDIR)/.config $($(PKG)_TARGET_DIR)/py.lst $($(PKG)_TARGET_DIR)/pyc.lst $($(PKG)_TARGET_DIR)/excluded-module-files.lst
	@echo -n "" > $@; \
	[ "$(FREETZ_PACKAGE_PYTHON3_PY)"  != y ] && cat $(PYTHON3_TARGET_DIR)/py.lst >> $@; \
	[ "$(FREETZ_PACKAGE_PYTHON3_PYC)" != y -o "$(FREETZ_PACKAGE_PYTHON3_COMPRESS_PYC)" == y ] && cat $(PYTHON3_TARGET_DIR)/pyc.lst >> $@; \
	(set -f; echo $(PYTHON3_UNNECESSARY_DIRS) | tr " " "\n" | sort >> $@); \
	[ "$(FREETZ_PACKAGE_PYTHON3_COMPRESS_PYC)" != y ] && echo "$(PYTHON3_ZIPPED_PYC)" >> $@; \
	cat $(PYTHON3_TARGET_DIR)/excluded-module-files.lst >> $@

$(pkg)-precompiled: $($(PKG)_STAGING_BINARY) $($(PKG)_TARGET_BINARY) $(if $(FREETZ_PACKAGE_PYTHON3_STATIC),,$($(PKG)_LIB_PYTHON3_TARGET_DIR)) $($(PKG)_ZIPPED_PYC_TARGET_DIR)

$(pkg)-clean:
	-$(SUBMAKE) -C $(PYTHON3_DIR) clean
	$(RM) $(PYTHON3_FREETZ_CONFIG_FILE)
	$(RM) $(PYTHON3_DIR)/.configured
	$(RM) $(PYTHON3_TARGET_DIR)/py.lst $(PYTHON3_TARGET_DIR)/pyc.lst
	$(RM) $(PYTHON3_TARGET_DIR)/excluded-module-files.lst $(PYTHON3_TARGET_DIR)/excluded-module-files-zip.lst $(PYTHON3_TARGET_DIR)/.exclude-extra
	$(RM) -r $(PYTHON3_LOCAL_INSTALL_DIR)
	$(RM) $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin/python*
	$(RM) -r $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/python$(PYTHON3_MAJOR_VERSION)
	$(RM) -r $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/python$(PYTHON3_MAJOR_VERSION)
	$(RM) $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libpython$(PYTHON3_MAJOR_VERSION).*
	$(RM) $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/python*

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_TARGET_BINARY) \
		$(PYTHON3_TARGET_LIBDIR)/libpython$(PYTHON3_MAJOR_VERSION).so* \
		$(PYTHON3_DEST_DIR)/usr/bin/python \
		$(PYTHON3_DEST_DIR)/usr/bin/python3 \
		$(PYTHON3_DEST_DIR)/usr/lib/python$(PYTHON3_MAJOR_VERSION) \
		$(PYTHON3_ZIPPED_PYC_TARGET_DIR) \
		$(PYTHON3_DEST_DIR)/usr/include/python$(PYTHON3_MAJOR_VERSION)

$(call PKG_ADD_LIB,libpython3)
$(PKG_FINISH)
