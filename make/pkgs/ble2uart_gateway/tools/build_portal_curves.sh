#!/bin/bash
set -euo pipefail

package_dir=$(realpath -- "$(dirname -- "${BASH_SOURCE[0]}")/..")
temporary=$(mktemp -d /tmp/ble-portal-curves.XXXXXX)
trap 'rm -rf "$temporary"' EXIT
npm install --prefix "$temporary" --ignore-scripts --no-audit --no-fund d3-shape@3.2.0 esbuild@0.25.12
cd "$temporary"
license=$(<node_modules/d3-shape/LICENSE)
printf '%s\n' 'export { curveMonotoneX } from "d3-shape";' |
    node_modules/.bin/esbuild --bundle --loader=js --format=iife --global-name=PortalCurves --minify \
        --banner:js="/*! d3-shape 3.2.0
$license
*/" \
        --outfile="$package_dir/files/root/usr/mww/ble2uart_gateway/portal-curves.js"