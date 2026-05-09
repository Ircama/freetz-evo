# hugo 0.161.1 (static site generator)
  - Homepage: [https://gohugo.io/](https://gohugo.io/)
  - Manpage / README: [https://gohugo.io/documentation/](https://gohugo.io/documentation/)
  - Changelog: [https://github.com/gohugoio/hugo/releases](https://github.com/gohugoio/hugo/releases)
  - Repository: [https://github.com/gohugoio/hugo](https://github.com/gohugoio/hugo)
  - Package: [../../make/pkgs/hugo/](../../make/pkgs/hugo/)
  - Steward: Ircama

`hugo` is a fast static site generator that can build documentation, blogs, and
small web sites directly on writable storage attached to the router.

## Runtime details in Freetz

- Binary path: `/usr/bin/hugo`
- Runtime dependency profile: self-contained Go binary built with `CGO_ENABLED=0`
- Externalization: supported for the binary

## Build notes

- The package cross-compiles the main upstream Go codebase into one executable.
- Site sources, caches, and generated output should live on USB or NAS storage because they can grow quickly.

## Typical usage

```sh
hugo --source /var/media/ftp/uStor01/site --destination /var/media/ftp/uStor01/site/public
```

Notes:
- `hugo server` may be useful for local previews, but persistent content should be generated into external storage.
- Large themes and content trees are better kept outside the firmware image.