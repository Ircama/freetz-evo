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

if ! grep -q 'name="DC.language" content="de"' "$news_html"; then
	perl -0pi -e 's|(<meta name="language" content="de">\n)|$1      <meta name="DC.language" content="de">\n|' "$news_html"
fi

if ! grep -q 'property="og:locale" content="de_DE"' "$news_html"; then
	perl -0pi -e 's|(<meta name="DC.language" content="de">\n)|$1      <meta property="og:locale" content="de_DE">\n|' "$news_html"
fi

if ! grep -q 'rel="alternate" hreflang="de"' "$news_html"; then
	perl -0pi -e 's|(<link rel="canonical" href="([^"]+)">\n)|$1      <link rel="alternate" hreflang="de" href="$2">\n|' "$news_html"
fi

perl -0pi -e 's|\s*<script type="application/ld\+json">\s*\{"":"https://schema\.org","":"WebPage","name":"[^"]+","inLanguage":"de-DE"\}\s*</script>\n?||g' "$news_html"
perl -0pi -e 's|(<script type="application/ld\+json">\s*\{"\@context":"https://schema\.org","\@type":"WebPage","name":")[^"]+(","inLanguage":"de-DE"\}\s*</script>)|$1Upstream Freetz-NG News$2|g' "$news_html"

if ! grep -q '"@context":"https://schema.org".*"inLanguage":"de-DE"' "$news_html"; then
	perl -0pi -e 's|(\n\s*</head>)|      <script type="application/ld+json">\n        {"\@context":"https://schema.org","\@type":"WebPage","name":"Upstream Freetz-NG News","inLanguage":"de-DE"}\n      </script>\n$1|' "$news_html"
fi

# The generated theme chrome is English and appears before the NEWS article.
# Mark it as non-translatable so language detectors weigh the German content.
perl -0pi -e '
	s|<div data-md-component="skip">|<div data-md-component="skip" lang="en" translate="no" class="notranslate">|;
	s|<div data-md-component="announce">|<div data-md-component="announce" lang="en" translate="no" class="notranslate">|;
	s|<header class="md-header md-header--shadow" data-md-component="header">|<header class="md-header md-header--shadow notranslate" data-md-component="header" lang="en" translate="no">|;
	s|<div class="md-search" data-md-component="search" role="dialog" aria-label="Search">|<div class="md-search notranslate" data-md-component="search" role="dialog" aria-label="Search" lang="en" translate="no">|;
	s|<div class="(md-sidebar(?![^"]*notranslate)[^"]*)"([^>]*)>|<div class="$1 notranslate"$2 lang="en" translate="no">|g;
	s|<footer class="md-footer">|<footer class="md-footer notranslate" lang="en" translate="no">|;
' "$news_html"

perl -0pi -e 's|<article class="md-content__inner md-typeset"[^>]*>|<article class="md-content__inner md-typeset" lang="de" translate="yes">|' "$news_html"

perl -0pi -e '
	s|<h1 id="neuigkeiten">Neuigkeiten|<h1 id="upstream-freetz-ng-news" lang="en" translate="no">Upstream Freetz-NG News|;
	s|href="#neuigkeiten"|href="#upstream-freetz-ng-news"|g;
' "$news_html"

if ! grep -q 'not Freetz-EVO release notes' "$news_html"; then
	perl -0pi -e 's|(<h1 id="upstream-freetz-ng-news"[^>]*>.*?</h1>\n)|$1<p lang="en" translate="no"><strong>Note:</strong> These entries are copied from upstream <a href="https://github.com/Freetz-NG/freetz-ng">Freetz-NG</a>. They are not Freetz-EVO release notes and may refer to upstream-only tags, discussions, or changes.</p>\n<p lang="en" translate="no">For an English machine translation, open the <a href="https://ircama-github-io.translate.goog/freetz-evo/NEWS/?_x_tr_sl=de&amp;_x_tr_tl=en&amp;_x_tr_hl=it&amp;_x_tr_pto=wapp">Google Translate version</a>.</p>\n|s' "$news_html"
fi

perl -0pi -e '
	s|<a href="([^"]*NEWS\.md)" title="Edit this page" class="md-content__button md-icon" rel="edit">|<a href="$1" title="Edit this page" class="md-content__button md-icon notranslate" rel="edit" lang="en" translate="no">|;
	s|<a class="headerlink" href="([^"]+)" title="Anchor link to this section">|<a class="headerlink notranslate" href="$1" title="Anchor link to this section" lang="en" translate="no">|g;
' "$news_html"

grep -q '<html lang="de" class="no-js">' "$news_html" || {
	echo "Failed to mark NEWS page HTML language as German" >&2
	exit 1
}

grep -q 'http-equiv="content-language" content="de"' "$news_html" || {
	echo "Failed to add NEWS content-language metadata" >&2
	exit 1
}

grep -q 'name="DC.language" content="de"' "$news_html" || {
	echo "Failed to add NEWS DC.language metadata" >&2
	exit 1
}

grep -q 'property="og:locale" content="de_DE"' "$news_html" || {
	echo "Failed to add NEWS Open Graph locale metadata" >&2
	exit 1
}

grep -q 'rel="alternate" hreflang="de"' "$news_html" || {
	echo "Failed to add NEWS hreflang alternate link" >&2
	exit 1
}

grep -q '"@context":"https://schema.org"' "$news_html" || {
	echo "Failed to add NEWS structured data context" >&2
	exit 1
}

grep -q '"@type":"WebPage"' "$news_html" || {
	echo "Failed to add NEWS structured data page type" >&2
	exit 1
}

grep -q '"inLanguage":"de-DE"' "$news_html" || {
	echo "Failed to add NEWS structured language metadata" >&2
	exit 1
}

grep -q '<article class="md-content__inner md-typeset" lang="de" translate="yes">' "$news_html" || {
	echo "Failed to mark NEWS article language as German" >&2
	exit 1
}

grep -q '<h1 id="upstream-freetz-ng-news" lang="en" translate="no">Upstream Freetz-NG News' "$news_html" || {
	echo "Failed to update NEWS page title" >&2
	exit 1
}

grep -q 'not Freetz-EVO release notes' "$news_html" || {
	echo "Failed to add NEWS upstream notice" >&2
	exit 1
}

grep -q 'ircama-github-io.translate.goog/freetz-evo/NEWS/' "$news_html" || {
	echo "Failed to add NEWS Google Translate link" >&2
	exit 1
}

grep -q '<header class="md-header md-header--shadow notranslate" data-md-component="header" lang="en" translate="no">' "$news_html" || {
	echo "Failed to mark NEWS theme chrome as non-translatable" >&2
	exit 1
}

grep -q '<a class="headerlink notranslate"' "$news_html" || {
	echo "Failed to mark NEWS header anchors as non-translatable" >&2
	exit 1
}
