#! /usr/bin/env bash
# generates thumbnails of docs/screenshots/* to docs/README/*_md.*
MYPWD="$(dirname $(realpath $0))"

for file in $MYPWD/*.???; do
	src="${file##*/}"
	ext="${src##*.}"
	dst="${src%.*}_md.${ext}"
	[ "${dst/_md_md./}" != "$dst" ] && continue
	case "${ext,,}" in
		svg)
			# SVG → PNG thumbnail via inkscape (convert/potrace cannot handle SVG→SVG)
			dst_png="${src%.*}_md.png"
			[ -e "$MYPWD/$dst_png" ] && continue
			echo "$src -> $dst_png"
			inkscape --export-type=png --export-filename="$MYPWD/$dst_png" \
				--export-height=333 "$MYPWD/$src" 2>/dev/null \
				&& chmod -x "$MYPWD/$src" "$MYPWD/$dst_png" 2>/dev/null \
				|| echo "  WARNING: inkscape failed for $src"
			;;
		*)
			[ -e "$MYPWD/$dst" ] && continue
			echo "$src -> $dst"
			${MAGICK:-convert} "$MYPWD/$src" -resize x333 "$MYPWD/$dst"
			chmod -x "$MYPWD/$src" "$MYPWD/$dst"
			;;
	esac
done
exit 0

