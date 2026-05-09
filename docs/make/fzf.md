# fzf 0.72.0 (fuzzy finder)
  - Homepage: [https://github.com/junegunn/fzf](https://github.com/junegunn/fzf)
  - Manpage / README: [https://github.com/junegunn/fzf#readme](https://github.com/junegunn/fzf#readme)
  - Changelog: [https://github.com/junegunn/fzf/releases](https://github.com/junegunn/fzf/releases)
  - Repository: [https://github.com/junegunn/fzf](https://github.com/junegunn/fzf)
  - Package: [../../make/pkgs/fzf/](../../make/pkgs/fzf/)
  - Steward: Ircama

`fzf` is a general-purpose fuzzy finder for interactive command-line filtering.
It can be used directly in shell pipelines on the target, especially over SSH.

## Runtime details in Freetz

- Binary path: `/usr/bin/fzf`
- Runtime dependency profile: self-contained Go binary built with `CGO_ENABLED=0`
- Externalization: supported for the binary

## Build notes

- The package builds the upstream Go sources into a single target binary.
- Shell integration helpers from upstream are not installed; the package focuses on the core executable.

## Typical usage

```sh
printf '%s\n' alpha beta gamma | fzf
```

Notes:
- `fzf` is most useful in interactive shells and remote SSH sessions.
- For large file trees or command histories, keep the working directory on writable external storage.