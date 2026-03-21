#!/usr/bin/env python3
"""Inject the Freetz EVO SSO preflight block into AriaNg's minified index.html.

Usage: inject_sso.py <snippet_html> <index_html>

The snippet is inserted immediately before the first jQuery <script src="js/jquery-...">
tag so it runs synchronously before AngularJS bootstraps.  The injection is
version-agnostic: it matches any jQuery filename that starts with "jquery-".
"""

import sys


def main():
    if len(sys.argv) != 3:
        print('Usage: inject_sso.py <snippet_html> <index_html>', file=sys.stderr)
        sys.exit(1)

    snippet_path = sys.argv[1]
    index_path = sys.argv[2]

    with open(snippet_path, 'r') as f:
        snippet = f.read().strip()

    with open(index_path, 'r') as f:
        content = f.read()

    # Inject before the first jQuery <script> tag (version-agnostic).
    marker = '<script src="js/jquery-'
    pos = content.find(marker)
    if pos == -1:
        print('SSO inject: WARNING: marker not found in ' + index_path +
              ' — SSO preflight NOT injected', file=sys.stderr)
        sys.exit(0)  # Non-fatal: don't break the build

    content = content[:pos] + snippet + content[pos:]

    with open(index_path, 'w') as f:
        f.write(content)

    print('SSO inject: preflight injected into ' + index_path)


if __name__ == '__main__':
    main()
