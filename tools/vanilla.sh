#! /usr/bin/env bash
[ "$(echo $USER | sha256sum)" != "804d5ac72a104f79eb8b3d4f537ed05207b711f717f4378008486749473ba70f  -" ] && echo "You dont want this" && exit 1
DL_DIR="$HOME/.freetz-dl"
GITDIR="$HOME/freetz-ng"
TOOLS_DIR="$GITDIR/tools"
TEMPDIR="/tmp/avmpack"
WORKDIR="$HOME/vanilla"
AVM_DIR="$WORKDIR/avm"
ORG_DIR="$WORKDIR/org"
PAK_DIR="$WORKDIR/pak"
VERSION='ADv2'


# patches vanilla 2 avm
# $1: avmdiff
vanilla2avm() {
	local avmdiff="$1"
	[ ! -e "$avmdiff" ] && echo "Usage: $0 vanilla2avm ~/.freetz-dl/avmdiff_*.patch.lzma" && exit 1
	[ ! -e MAINTAINERS ] && echo "This direcory does not look like an unpacked kernel" && exit 1
	local KERNEL_SOURCE_DIR='.'
	"$TOOLS_DIR/freetz_patch" "$KERNEL_SOURCE_DIR" $avmdiff
	find "$KERNEL_SOURCE_DIR" -type l -exec rm -f {} ';'
	"$TOOLS_DIR/lzma" d $avmdiff -so | grep -E '^    #FREETZ# (mkdir|chmod|slink|touch) .*' | while read x a b c; do
		echo "$a: $b $c"
		[ "$a" != "mkdir" ] && [ "$b" != "${b%/*}" ] && mkdir -p   "$KERNEL_SOURCE_DIR/${b%/*}"
		[ "$a" == "mkdir" ] && mkdir -p   "$KERNEL_SOURCE_DIR/${b}"
		[ "$a" == "chmod" ] && touch      "$KERNEL_SOURCE_DIR/${b}"
		[ "$a" == "chmod" ] && chmod +x   "$KERNEL_SOURCE_DIR/${b}"
		[ "$a" == "slink" ] && ln -s "$c" "$KERNEL_SOURCE_DIR/${b}"
		[ "$a" == "touch" ] && touch      "$KERNEL_SOURCE_DIR/${b}"
	done
}


# gets kerner version
# $1: directory
get_kernel_version() {
	local DIR="${1:-.}"
	local CFG="$(sed -n 's/.*KCONFIG_CONFIG = //p' $DIR/linux*/.kernelvariables 2>/dev/null)"
	[ -n "$CFG" ] && CFG="$DIR/linux*/$CFG" || CFG="$DIR/linux*/.config"
	grep -E 'Kernel Configuration|Linux kernel version' $CFG 2>/dev/null | grep -v '^$' | head -n1 | sed 's/x86//;s/arm64//' | sed 's/[^0-9\.]//g' | sed 's/^$/UNKNOWN/g'
}

# creates vanilla patch 4 avm
# $1: (optional) avm (tiny) kernel pack
# $2: (optional) vanilla kernel version
# $3: (optional) SOURCE_ID = XXXX_XX.XX
vanilla4avm() {
	mkdir -p "$WORKDIR"
	local out="$1" avm="$2" org hwr="$3"
	[ -z "$hwr" ] && hwr="${out##*/}" && hwr="${hwr%%-*}"

	# check/unpack avmpack
	if [ -n "$out" ]; then
		[ ! -e "$out" ] && echo "Missing: $out" && exit 1
		echo "Unpack ${out##*/}"
		rm -rf "$TEMPDIR"
		mkdir -p "$TEMPDIR"
		ln -sf "$TEMPDIR" "$AVM_DIR"
		tar xf "$out" -C "$AVM_DIR"
	fi
	[ ! -e $AVM_DIR ] && echo "echo Put AVM's kernel sources unpacked into $AVM_DIR" && exit 1

	# avms crippled version
	avm="${avm:-$(get_kernel_version "$AVM_DIR")}"
	[ -z "$avm" ] && avm='2.6.13.1'
	[ "$avm" == '2.6.28.8' ] && avm='2.6.28.10'
	echo "avm=$avm"

	# used vanilla version
	org="$avm"
	[ "$avm" == '2.6.19.2' ] && org='2.6.19'
	[ "${avm%.*}" == '2.6.32' ] && org='2.6.32.27'
	echo "org=$org"

	# check/unpack vanilla
	if [ ! -e "$ORG_DIR/linux-$avm" ]; then
		[ ! -e "$DL_DIR/linux-$org.tar.xz" ] && echo "Missing: $DL_DIR/linux-$org.tar.xz" && exit 1
		echo "Kernel linux-$avm.tar.xz"
		mkdir -p "$ORG_DIR"
		tar xf "$DL_DIR/linux-$org.tar.xz" -C "$ORG_DIR"
	fi

	# create avmdiff
	mkdir -p "$PAK_DIR"
	local output="$PAK_DIR/avmdiff_$avm-${hwr:-XXXX_XX.XX}-$VERSION.patch"
	cd "$WORKDIR"
cat > "$output" <<EOX

This patch has been created from AVM's opensrc packages: https://osp.avm.de/
    diff -Naur --no-dereference org/linux-$org avm/linux* > this.patch

$(for x in $(find avm/linux* -type d -empty        ); do echo "    #FREETZ# mkdir ${x#avm/linux*/}"               ; done)
$(for x in $(find avm/linux* -type f -a -executable); do echo "    #FREETZ# chmod ${x#avm/linux*/}"               ; done)
$(for x in $(find avm/linux* -type l               ); do echo "    #FREETZ# slink ${x#avm/linux*/} $(readlink $x)"; done)
$(for x in $(find avm/linux* -type f -empty        ); do echo "    #FREETZ# touch ${x#avm/linux*/}"               ; done)

EOX
	diff -Naur --no-dereference org/linux-$org avm/linux* >> "$output" 2>/dev/null
#	return
	touch -d "2021-05-26 17:15:00.000000000 +0200" "$output"
	local packed="$output.lzma"
	du -sh "$output"
	echo "Packing $packed"
	rm -f "$packed" 2>/dev/null
	"$TOOLS_DIR/lzma" e "$output" "$packed" -d25
	du -sh "$packed"
	sha256sum "$packed"
	rm -f "$output" 2>/dev/null
	touch -d "2021-05-26 17:15:00.000000000 +0200" "$packed"
}


# ADv0 -> ADv1
generate_vanilla() {
	local OLD_VER='avm'

	for x in $DL_DIR/kernel_*-$OLD_VER.patch.xz; do
		m="$(echo $x| sed "s/-$OLD_VER.patch.xz$//;s/.*-//")"
		$0 vanilla4avm $DL_DIR/fw/$m-release_kernel.tar.xz
	done

	# 6660_07.39
	rm -f kernel_4.9.250-6660_07.39.x86-*.patch
	$0 vanilla4avm "$DL_DIR/fw/6660_07.39.x86-release_kernel.tar.xz" "4.9.279"

	# 7582_07.15
	rm -f kernel_2.6.13.1-7582_07.15-*.patch
	rm -f "$AVM_DIR"
	ln -sf "$TEMPDIR/kernel" "$AVM_DIR"
	rm -rf "$TEMPDIR"
	mkdir -p "$TEMPDIR"
	tar xf "$DL_DIR/fw/7582_07.15-release_kernel.tar.xz" -C "$TEMPDIR"
	$0 vanilla4avm "" "4.1.38" "7582_07.15"

	# update hash
	for x in $PAK_DIR/kernel_*.patch.xz; do
		local file=${x##*/}
		local OLD_HASH="$(sha256sum $DL_DIR/${file/$VERSION/$OLD_VER})"
		local NEW_HASH="$(sha256sum $x)"
		grep -q "${OLD_HASH%% *}" $GITDIR/config/mod/dl-kernel.in || echo "Not found: $file"
		sed "s/${OLD_HASH%% *}/${NEW_HASH%% *}/" -i $GITDIR/config/mod/dl-kernel.in
	done
}


help() {
echo "Usage: $0 <vanilla2avm|vanilla4avm|generate_vanilla>"
cat <<'EOX'

        vanilla2avm - patches unpacked vanilla kernel sources 2 avm with a avmdiff
        vanilla4avm - creates avmdiff file from vanilla kernel 4 avm sources
        generate_vanilla - initial used to create avmdiff from tiny kernel pack files

        Add kernel source, create avmdiff (example: 7590 FOS 08.50):
        Unpack avm sources
        #
        mkdir -p ~/vanilla
        rm -rf ~/vanilla/avm
        ln -sf $(realpath sources/kernel) ~/vanilla/avm
        ~/freetz-ng/tools/vanilla.sh vanilla4avm "" "" "7590_08.50"  # generate avm-diff
        #
        ge ~/freetz-ng/docs/CHANGELOG.md  # AVM sources
        ge ~/freetz-ng/config/mod/dl-kernel.in  # add hash
        ls ~/vanilla/pak/avmdiff_*.patch.lzma  # upload file
        rm -rf ~/vanilla/  # cleanup vanilla.sh
        ge ~/freetz-ng/config/avm/source.in  # add avm-source
        ge ~/freetz-ng/config/avm/kernel.in  # add kernel version (should exist)
        #
        #grep KCONFIG sources/kernel/linux*/.kernelvariables  # get config name
        realpath $(dirname sources/kernel/linux*/.kernelvariables)/$(sed -n 's,.*_KCONFIG_.* = ,,p' sources/kernel/linux*/.kernelvariables)
        add ~/freetz-ng/make/kernel/configs/freetz/config-*-7590_*
        add ~/freetz-ng/make/kernel/configs/avm/config-*-7590_*
        #
        realpath conf/buildroot/busybox.config*
        add ~/freetz-ng/make/busybox/avm/*-7590--busybox.config.*
        #
        add ~/freetz-ng/make/kernel/patches/*/7590_*/
        ge ~/freetz-ng/config/mod/source.in  # enable kernel (modules)
        ge ~/freetz-ng/make/pkgs/wireguard-linux-compat/Config.in  # verify skb_put_data
        check if avms .config matches with provided sources (unlikely)

EOX
}


[ -n "$1" ] && [ ! -x "$TOOLS_DIR/lzma" ] && echo "Tool 'lzma' missing. Run 'make lzma1-host' first." && exit 1

case "$1" in
	vanilla2avm)		shift; vanilla2avm "$@" ;;
	vanilla4avm)		shift; vanilla4avm "$@" ;;
	generate_vanilla)	shift; generate_vanilla ;;
	*)			help                    ;;
esac


rm -rf "$TEMPDIR"
exit
