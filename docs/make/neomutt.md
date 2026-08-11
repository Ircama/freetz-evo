# NeoMutt 20260504 (binary only)
  - Homepage: [https://neomutt.org/](https://neomutt.org/)
  - Manpage: [https://neomutt.org/guide/](https://neomutt.org/guide/)
  - Changelog: [https://github.com/neomutt/neomutt/releases](https://github.com/neomutt/neomutt/releases)
  - Repository: [https://github.com/neomutt/neomutt](https://github.com/neomutt/neomutt)
  - Package: [master/make/pkgs/neomutt/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/neomutt/)
  - Steward: Ircama
  - Toolchain: requires GCC 4.7 or newer (`FREETZ_TARGET_GCC_4_7_MIN` in `Config.in`): NeoMutt's configure requires C11 (`-std=c11`), which the old GCC 4.6.4 toolchain does not support (`Error: C11 is required`). This is a GCC issue, not uClibc-specific: uClibc 1.0.14 with GCC 5.5 builds fine.

**NeoMutt** is a command-line mail user agent (MUA) derived from the classic Mutt client. It adds
many features that were never merged into the Mutt upstream: improved sidebar, virtual mailboxes,
conditional formatting, notmuch search integration (disabled in this package), NNTP reading, and
an active community-maintained patch set. Despite the rich feature set, NeoMutt keeps Mutt's
keyboard-centric workflow intact and is fully scriptable through hook commands, macros, and an
extensive `muttrc` configuration language.

The Freetz-EVO package cross-compiles NeoMutt using its `autosetup`-based `configure` script,
linking against the `ncursesw` and `openssl` libraries already present in the Freetz toolchain
staging directory.

## Runtime details in Freetz

- Binary path: `/usr/bin/neomutt`
- Runtime dependencies: `ncursesw`, `libssl` / `libcrypto` (OpenSSL)
  - On targets with uClibc 0.9.28 the `iconv` library is also linked
- Externalization: supported for the binary; `libncursesw` and OpenSSL must also be present on
  the target (enable their respective `EXTERNAL_FREETZ_LIB_*` options if needed)
- Typical storage location: the binary can remain in flash (`/usr/bin/neomutt`); the mailbox
  and configuration should live on writable external storage (USB/NAS)

## Build notes

- NeoMutt uses an `autosetup`-based build system, not standard autoconf, so the generic
  Freetz `PKG_CONFIGURED_CONFIGURE` helper (which adds `--cache-file` and similar options)
  is not used. A custom `.configured` rule invokes `./configure` directly with
  `--host`, `--build`, `--prefix`, and explicit staging-directory paths for ncurses and OpenSSL.
- Documentation generation is disabled (`--disable-doc`) to avoid a build-time dependency on
  DocBook tools not present in the Freetz host environment.
- NLS, IDN2, GPGME, GnuTLS, GSASL, Cyrus-SASL, Lua, notmuch, SQLite, TokyoCabinet, and LMDB
  are all disabled to minimise dependencies and binary size.
- RPATH hardcoding is prevented via `PKG_PREVENT_RPATH_HARDCODING` so the binary finds
  libraries correctly at runtime on the target.

## Compile-time options summary

| Option | Value |
|--------|-------|
| TLS/SSL backend | OpenSSL (`--ssl --with-ssl`) |
| Ncurses | Wide-character `ncursesw` (`--with-ncurses`) |
| Documentation | disabled |
| NLS / gettext | disabled |
| IDN2 | disabled |
| GPGME | disabled |
| GnuTLS | disabled |
| SASL / GSASL | disabled |
| Lua scripting | disabled |
| Notmuch | disabled |
| SQLite | disabled |
| TokyoCabinet / LMDB | disabled |

## Typical usage

### Minimal muttrc for a local Maildir

Store this at `/root/.muttrc` (or on external storage and symlink):

```sh
set mbox_type = Maildir
set folder    = /var/media/ftp/uStor01/mail
set spoolfile = +INBOX
set record    = +Sent
set postponed = +Drafts
set trash     = +Trash

# Display
set sort      = threads
set sort_aux  = reverse-last-date-received
set pager_index_lines = 10
```

### IMAP with TLS (e.g. Gmail)

```sh
set imap_user       = user@gmail.com
set folder          = imaps://imap.gmail.com/
set spoolfile       = +INBOX
set ssl_starttls    = yes
set ssl_force_tls   = yes
```

### Key bindings (defaults)

| Key | Action |
|-----|--------|
| `j` / `↓` | next message |
| `k` / `↑` | previous message |
| `Enter` | open message |
| `q` | quit / close |
| `m` | compose new message |
| `r` | reply |
| `R` | group reply |
| `f` | forward |
| `d` | delete |
| `$` | sync mailbox |
| `/` | search |
| `c` | change mailbox |
| `s` | save message |

Notes:
- NeoMutt is best operated over SSH; it requires a UTF-8 terminal for proper wide-character
  rendering (e.g. PuTTY with `UTF-8` encoding, or any modern terminal emulator).
- For SMTP sending, configure `set smtp_url = smtps://user@smtp.example.com` and store the
  password in `~/.netrc` or the NeoMutt credential helpers.
- The FritzBox system clock must be synchronised (NTP) before attempting TLS connections;
  certificate expiry checks will fail if the clock is wrong.
