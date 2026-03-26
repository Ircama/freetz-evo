---
title: Repository README
---

[//]: # ( This page dynamically includes the repository root README.md. )

--8<-- "README.md"

<script>
(() => {
	const marker = "/REPO_README/";

	const normalizePath = (value) => {
		if (!window.location.pathname.includes(marker)) {
			return value;
		}

		const idx = window.location.pathname.indexOf(marker);
		const basePrefix = idx >= 0 ? window.location.pathname.slice(0, idx + 1) : "/";
		const absDocsPrefix = `${basePrefix}docs/`;

		if (!value || value.includes("://") || value.startsWith("mailto:") || value.startsWith("tel:")) {
			return value;
		}

		if (value.startsWith("../docs/")) {
			return "../" + value.slice("../docs/".length);
		}

		if (value.startsWith("docs/")) {
			return "../" + value.slice("docs/".length);
		}

		if (value.startsWith(absDocsPrefix)) {
			return `${basePrefix}${value.slice(absDocsPrefix.length)}`;
		}

		return value;
	};

	const normalizeElement = (el) => {
		const key = el.hasAttribute("href") ? "href" : "src";
		const current = el.getAttribute(key);
		const normalized = normalizePath(current);
		if (normalized !== current) {
			el.setAttribute(key, normalized);
		}
	};

	const normalizeLinks = () => {
		if (!window.location.pathname.includes(marker)) {
			return;
		}

		document.querySelectorAll("article a[href], article img[src]").forEach((el) => {
			normalizeElement(el);
		});
	};

	if (!window.__repoReadmeLinkFixInstalled) {
		window.__repoReadmeLinkFixInstalled = true;
		document.addEventListener("click", (ev) => {
			const target = ev.target;
			if (!target || !target.closest) {
				return;
			}
			const link = target.closest("article a[href]");
			if (link) {
				normalizeElement(link);
			}
		}, true);
	}

	normalizeLinks();
	requestAnimationFrame(normalizeLinks);
})();
</script>
