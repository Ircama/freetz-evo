#!/bin/sh
# Copy host Perl modules needed for the microperl 5.38 build.
# Called from PATCH_POST_CMDS - executed from the unpacked source directory.
#
# Uses "perl -M<Mod> -e 'print $INC{...}'" to locate each module on the
# current host regardless of Perl version or install prefix, so this works
# on Debian/Ubuntu 22.04, 24.04, CI runners, etc.

copy_module() {
	local module="$1"   # Perl module name, e.g. Cwd
	local inckey="$2"   # Key in %INC, e.g. Cwd.pm
	local destdir="$3"  # Destination inside lib/, e.g. . or File or Class

	local src
	src=$(perl -M"$module" -e "print \$INC{'$inckey'}" 2>/dev/null)

	if [ -z "$src" ] || [ ! -f "$src" ]; then
		echo "Warning: $module ($inckey) not found on this host, skipping" >&2
		return 0
	fi

	mkdir -p "lib/$destdir"
	cp -f "$src" "lib/$destdir/"
}

# Modules in the root lib/ directory
copy_module Cwd          Cwd.pm          .
copy_module overload     overload.pm     .

# Modules in subdirectories
copy_module File::Spec   File/Spec.pm    File
copy_module File::Temp   File/Temp.pm    File
copy_module Class::Struct  Class/Struct.pm  Class
copy_module Data::Dumper   Data/Dumper.pm   Data
copy_module Getopt::Long   Getopt/Long.pm   Getopt
copy_module IO::File       IO/File.pm       IO
copy_module Scalar::Util   Scalar/Util.pm   Scalar
