# yq 4.53.2 (YAML/JSON/XML processor)
  - Homepage: [https://github.com/mikefarah/yq](https://github.com/mikefarah/yq)
  - Manpage / README: [https://mikefarah.gitbook.io/yq/](https://mikefarah.gitbook.io/yq/)
  - Changelog: [https://github.com/mikefarah/yq/releases](https://github.com/mikefarah/yq/releases)
  - Repository: [https://github.com/mikefarah/yq](https://github.com/mikefarah/yq)
  - Package: [../../make/pkgs/yq/](../../make/pkgs/yq/)
  - Steward: Ircama

`yq` is a command-line processor for YAML, JSON, XML, and related structured
data formats. It is useful for config rewriting, scripted administration, and
pipeline-based transformations on the target.

## Runtime details in Freetz

- Binary path: `/usr/bin/yq`
- Runtime dependency profile: self-contained Go binary built with `CGO_ENABLED=0`
- Externalization: supported for the binary

## Build notes

- The package cross-compiles the upstream Go sources into a single executable.
- No Python runtime or external YAML tooling is needed on the target.

## Typical usage

```sh
yq '.services[0].name' /var/media/ftp/uStor01/config/example.yaml
```

Notes:
- `yq` is useful for scripted maintenance of YAML-heavy application configs stored on writable media.
- The same binary can also process JSON input, which helps on mixed-format admin tasks.