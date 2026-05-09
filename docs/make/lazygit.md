# lazygit 0.61.1 (terminal Git UI)
  - Homepage: [https://github.com/jesseduffield/lazygit](https://github.com/jesseduffield/lazygit)
  - Manpage / README: [https://github.com/jesseduffield/lazygit#readme](https://github.com/jesseduffield/lazygit#readme)
  - Changelog: [https://github.com/jesseduffield/lazygit/releases](https://github.com/jesseduffield/lazygit/releases)
  - Repository: [https://github.com/jesseduffield/lazygit](https://github.com/jesseduffield/lazygit)
  - Package: [../../make/pkgs/lazygit/](../../make/pkgs/lazygit/)
  - Steward: Ircama

`lazygit` is a full-screen terminal UI for common Git workflows such as status review,
staging, commits, branch switching, rebases, cherry-picks, stash handling, and log browsing.
The Freetz-EVO package cross-compiles the upstream Go sources into a single target binary.

## Runtime details in Freetz

- Binary path: `/usr/bin/lazygit`
- Main runtime dependency: `git`
- Externalization: supported for the binary
- Typical storage location: run it inside a Git working tree stored on writable USB or NAS media

## Build notes

- The package is built with Go cross-compilation and `CGO_ENABLED=0`, producing a self-contained binary for the selected target architecture.
- Upstream vendored modules are used during the build, so no module download is needed while compiling in Freetz-EVO.
- The shared Freetz-EVO Go host toolchain is updated to 1.25.10 for `lazygit` and other Go-based packages such as `gh`.

## Typical usage

```sh
cd /var/media/ftp/uStor01/projects/my-repo
lazygit
```

Notes:
- `lazygit` shells out to `git`, so the package automatically selects the Freetz `git` package.
- The interface is terminal-based and is best used over SSH or from a local shell session on the box.