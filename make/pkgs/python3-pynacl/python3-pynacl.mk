$(call PKG_INIT_BIN, 1.6.2)
$(PKG)_SOURCE:=pynacl-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=pynacl-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/p/pynacl
$(PKG)_HASH:=018494d6d696ae03c7e656e5e74cdfd8ea1326962cc401bcf018f1ed8436811c
### WEBSITE:=https://github.com/pyca/pynacl
### CHANGES:=https://github.com/pyca/pynacl/releases
### CVSREPO:=https://github.com/pyca/pynacl
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-cffi

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/nacl/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	@printf '%s\n' \
		"import io" \
		"import os" \
		"import sys" \
		"" \
		"f = '$(PYTHON3_PYNACL_DIR)/setup.py'" \
		"if not os.path.exists(f):" \
		"    sys.exit('Freetz python3-pynacl.mk: File not found: %s' % f)" \
		"" \
		"with io.open(f, 'r', encoding='utf-8') as fh:" \
		"    src = fh.read()" \
		"" \
		"if 'LIBSODIUM_CONFIGURE_ARGS' not in src:" \
		"    src = src.replace(" \
		"        '        if os.environ.get(\"SODIUM_INSTALL_MINIMAL\"):\\n'" \
		"        '            configure_flags.append(\"--enable-minimal\")\\n'" \
		"        '        subprocess.check_call(\\n'," \
		"        '        if os.environ.get(\"SODIUM_INSTALL_MINIMAL\"):\\n'" \
		"        '            configure_flags.append(\"--enable-minimal\")\\n'" \
		"        '        if os.environ.get(\"LIBSODIUM_CONFIGURE_ARGS\"):\\n'" \
		"        '            configure_flags.extend(os.environ[\"LIBSODIUM_CONFIGURE_ARGS\"].split())\\n'" \
		"        '        subprocess.check_call(\\n'" \
		"    )" \
		"" \
		"if 'PYNACL_SKIP_TESTS' not in src:" \
		"    src = src.replace(" \
		"        '        # Check the build library\\n'" \
		"        '        subprocess.check_call(\\n'" \
		"        '            [make_command, \"check\"] + make_args, cwd=build_temp\\n'" \
		"        '        )\\n\\n'," \
		"        '        # Check the build library\\n'" \
		"        '        if not os.environ.get(\"PYNACL_SKIP_TESTS\"):\\n'" \
		"        '            subprocess.check_call(\\n'" \
		"        '                [make_command, \"check\"] + make_args, cwd=build_temp\\n'" \
		"        '            )\\n\\n'" \
		"    )" \
		"" \
		"with io.open(f, 'w', encoding='utf-8') as fh:" \
		"    fh.write(src)" \
	| $(TOOLS_DIR)/path/python3
	$(call Build/PyMod3/Pip, PYTHON3_PYNACL, , \
		SODIUM_INSTALL=bundled \
		LIBSODIUM_CONFIGURE_ARGS="--host=$(call qstrip,$(FREETZ_TARGET_UCLIBC_TRIPLET))" \
		PYNACL_SKIP_TESTS=1 \
		CPATH="$(PYTHON3_STAGING_INC_DIR)" \
		CPPFLAGS="$(TARGET_CPPFLAGS) -I$(PYTHON3_STAGING_INC_DIR)" \
		CFLAGS="$(TARGET_CFLAGS) -I$(PYTHON3_STAGING_INC_DIR)" \
		CXXFLAGS="$(TARGET_CXXFLAGS) -I$(PYTHON3_STAGING_INC_DIR)" \
		LDFLAGS="$(TARGET_LDFLAGS) -L$(PYTHON3_STAGING_LIB_DIR)" \
	, isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_PYNACL_DIR)/.configured
	$(RM) -r $(PYTHON3_PYNACL_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_PYNACL_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/nacl \
		$(PYTHON3_PYNACL_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/pynacl-*.dist-info

$(PKG_FINISH)
