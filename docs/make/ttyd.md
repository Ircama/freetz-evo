# ttyd 1.7.7
  - Homepage: [https://github.com/tsl0922/ttyd](https://github.com/tsl0922/ttyd)
  - Manpage: [https://github.com/tsl0922/ttyd/blob/main/man/ttyd.1](https://github.com/tsl0922/ttyd/blob/main/man/ttyd.1)
  - Changelog: [https://github.com/tsl0922/ttyd/releases](https://github.com/tsl0922/ttyd/releases)
  - Repository: [https://github.com/tsl0922/ttyd](https://github.com/tsl0922/ttyd)
  - Package: [master/make/pkgs/ttyd/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/ttyd/)
  - Steward: -
  - Maintainer: -

# ttyd – Feature Overview

**ttyd** is a lightweight tool that exposes a local terminal session over a web interface. It acts as a bridge between a PTY (pseudo-terminal) and a browser-based client.

It is typically used to provide remote shell access without SSH clients, using only a browser.

ttyd is a **terminal-to-web bridge** providing:

* full interactive shell in browser
* WebSocket-based real-time I/O
* minimal runtime overhead
* strong suitability for embedded and headless systems
* full keyboard input (including control sequences)
* clipboard integration (browser-dependent)
* real-time stdout/stderr streaming
* resize events forwarded to PTY

---

## Core architecture

ttyd implements a simple model:

Terminal process (bash/sh/any CLI) ⇄ PTY ⇄ ttyd server ⇄ WebSocket ⇄ Browser

Key properties:

* each browser session attaches to a pseudo-terminal
* full bidirectional I/O streaming
* low latency via WebSocket transport

---

## Session handling

* spawns a configurable shell or command
* multiple concurrent sessions supported
* each session is isolated at PTY level
* automatic session cleanup on disconnect

---

## Web interface

* single-page web UI
* terminal emulation via xterm.js-style rendering
* full ANSI escape sequence support:

  * colors
  * cursor movement
  * screen buffers
* responsive layout for mobile and desktop
