#!/usr/bin/env bash
set -euo pipefail

site_dir="${1:-.github/zensical/site}"
news_html="${site_dir%/}/NEWS/index.html"

if [[ ! -f "$news_html" ]]; then
	echo "NEWS page not found: $news_html" >&2
	exit 1
fi

perl -0pi -e 's/<html lang="[^"]+"/<html lang="de"/' "$news_html"

if ! grep -q 'http-equiv="content-language" content="de"' "$news_html"; then
	perl -0pi -e 's|(<meta charset="utf-8">\n)|$1      <meta http-equiv="content-language" content="de">\n      <meta name="language" content="de">\n|' "$news_html"
fi

perl -0pi -e 's/<article class="md-content__inner md-typeset">/<article class="md-content__inner md-typeset" lang="de">/' "$news_html"

grep -q '<html lang="de" class="no-js">' "$news_html" || {
	echo "Failed to mark NEWS page HTML language as German" >&2
	exit 1
}

grep -q 'http-equiv="content-language" content="de"' "$news_html" || {
	echo "Failed to add NEWS content-language metadata" >&2
	exit 1
}

grep -q '<article class="md-content__inner md-typeset" lang="de">' "$news_html" || {
	echo "Failed to mark NEWS article language as German" >&2
	exit 1
}
