# Freetz-EVO — The Audio Subsystem

With the Freetz-EVO Audio Subsystem, a FRITZ!Box connected to a USB DAC can function as an audio endpoint, providing audio server, receiver, and player functionality, as well as control of the attached DAC, including some high-end features.

FRITZ!Box devices do not provide an analog sound card, line-out, or onboard audio codec intended for direct user access. The stock firmware also does not expose the kernel's audio subsystem. Freetz-EVO therefore uses **USB audio** as its primary audio interface: the FRITZ!Box can provide audio playback and processing when a **USB Audio Class device — preferably a USB HiFi DAC, or alternatively a USB headset — is attached**. The required software and drivers are integrated into the custom firmware so that the USB audio device can be detected, accessed, and configured directly on the box.

"Activating audio" in Freetz-EVO consequently means three coordinated things:

1. exposing and enabling the **kernel-side sound drivers** that the underlying AVM kernel tree already contains but does not surface;
2. adding the **ALSA userspace stack** (library, configuration tree, command-line tools, CGI GUI) so that applications can open a PCM device; and
3. shipping the **applications and web interfaces** that actually produce, receive, process and control sound.

## Exposing the hidden kernel drivers

The lowest layer is the **ALSA USB Audio Kernel Support**. On targets whose AVM kernel sources already contain ALSA USB support, Freetz-EVO exposes the corresponding module toggles in menuconfig, turning a hidden capability into a set of selectable build options. The modules brought into play are the standard ALSA chain: `soundcore`, `snd`, `snd-timer`, `snd-pcm`, `snd-hwdep`, `snd-rawmidi`, `snd-usbmidi-lib` and, at the top, `snd-usb-audio`.

Crucially, the userspace package does the wiring for you. On compatible targets, selecting `alsa-utils` also auto-selects the USB audio kernel driver stack exposed in menuconfig, so a USB DAC can be brought up without manually chasing the required `snd*` modules." The same auto-selection is triggered by several of the applications (go-librespot, shairport-sync, cmus, ...), all of which reflect the same assumption: the intended hardware is a USB DAC or soundcard plugged into the FRITZ!Box device.

The resulting audio path is simple and entirely USB-based:

> **USB HiFi DAC / USB headset → `snd-usb-audio` → ALSA (`alsa-lib`) → application**

## Both directions: microphone input and audio output

ALSA on Freetz-EVO is not output-only. The kernel layer can expose USB audio interfaces (playback/capture) and USB-MIDI devices through ALSA, and the userspace tools cover both directions:

- **Output / playback** — `alsa-lib` is the base for playback; `alsa-utils` provides `aplay` and `speaker-test`;
- **Input / capture** — `alsa-lib` is equally the base for capture; `alsa-utils` provides `arecord` and capture-device enumeration (`arecord -l`);
- **MIDI** — `snd-rawmidi` and `snd-usbmidi-lib` plus the sequencer/MIDI utilities in `alsa-utils` allow USB-MIDI devices to be used as well.

Runtime verification is done with familiar commands: `lsmod | grep -E "snd|usb_audio|snd_usb"`, `cat /proc/asound/card*/stream0`, `cat /proc/asound/card*/usbmixer`, and `aplay -l` / `arecord -l`.

## The governing constraint: no hardware FPU

Everything distinctive about the way Freetz-EVO configures audio flows from a single hardware fact: many FritzBox SoCs (e.g. GRX550 MIPS32) lack a hardware FPU. Floating-point operations in audio processing (sample rate conversion, equalization) are emulated in software, which overwhelms the CPU and causes stuttering.

Because floating-point maths is emulated in software on many SoCs, any audio operation that leans on it — most importantly **sample-rate conversion** and **equalization** — is ruinously expensive and produces drop-outs. The project's design responds to this in three deliberate ways.

### Consequence 1 — sample-rate conversion is disabled in the ALSA configuration

Rather than let ALSA silently resample in software, the build ships an ALSA configuration that steers away from floating-point conversion entirely. The build system sets:

- `defaults.pcm.rate_converter linear` (integer-only, no FPU, unacceptable audio quality)
 - `pcm.default pcm.plughw` (bypasses ALSA mixer, uses hw-native rates)

Applications should be configured to use ALSA device `hw:0,0` (direct hardware access) instead of `default` (which may trigger resampling).

In other words, the resampling code is not removed but is pinned to the cheapest integer-only path, and — more importantly — applications are told to open the hardware device directly (`hw:0,0`) so that **no resampling happens at all**. Even if the software comes with all converters, including the top and low-quality ones, none is recommended for music playback. Low-quality converters like `linear`, `lavcrate_faster`, `samplerate_order`, `samplerate_linear` are not appropiate for hifi sound. For music, stick with `hw:0,0` to avoid resampling entirely.

This pushes a hardware requirement onto the DAC itself: USB audio cards used with soft-float targets should support the most common sample rates 44100 Hz and 48000 Hz natively in hardware. If a card does not support these rates, ALSA must resample in software, which triggers FPU emulation and overloads the CPU.

The preferred sample formats are `S16_LE` and `S24_3LE`, and a DAC that natively handles both the 44.1 kHz and 48 kHz families avoids conversion for essentially all common material.

### Consequence 2 — `alsaequal` works, but is a developer-only option

Software equalization is subject to the same penalty as software resampling, and the project handles it the same way. The **`alsaequal`** plugin has been ported and genuinely works — it exposes a LADSPA-based equalizer through ordinary ALSA PCM and control devices, backed by the CAPS LADSPA suite's ten-band `Eq10` module — but it is flagged **DEVELOPER** and left disabled by default. The reason, again, is CPU cost on emulated-FPU parts: it depends on heavy floating-point computation (IIR/EQ filtering via `ladspa` / `caps`) and software-emulated FPU makes it unusable.

The penalty is most acute precisely on the CPUs that emulate the FPU. So `alsaequal` remains available for experimentation and for the targets with enough headroom, but it is not part of the normal audio path.

### Consequence 3 — move DSP off the CPU and into the DAC

The logical resolution of a system that cannot afford software EQ or resampling is to **do that work in dedicated hardware**. This is why Freetz-EVO invests so heavily in USB-Audio DACs that carry their own DSP, and specifically why it ships tooling to configure those DACs over HID (covered in depth subsequently). Equalization, digital filtering and gain are performed inside the DAC's own DSP, entirely off the CPU of the FRITZ!Box device; the FRITZ!Box merely streams clean, un-resampled PCM to it. The disabled `alsaequal` and the elaborate `ja11-config` / `hidws` tooling are two ends of this design decision.

---

## The ALSA foundation

All configuration settings related to the audio capabilities of Freetz-EVO are included in the dedicated **Packages → Audio** section of `make menuconfig`.

The tools used to configure and manage USB DACs are available under **Packages → Flasher tools** in `make menuconfig`, including:

- **`hidws`**, HID/WebSocket gateway together with its CGI interface
- **`ja11-config`** (firmware update and an advanced PEQ/filter/gain TUI for the JA11)

### `alsa-lib` 1.2.13 — the userspace runtime

`alsa-lib` is the userspace runtime for ALSA: it provides `libasound.so.2` and installs the shared ALSA configuration tree under `/usr/share/alsa`, which is what makes device discovery and PCM definitions work on the target. It is the common base for playback, capture, mixer access and AirPlay output and is depended on by `alsa-utils`, `cmus`, `shairport-sync` and the rest. As described in the previous section, it is here that the FPU-avoiding defaults (`rate_converter linear`, `pcm.default pcm.plughw`, the `hw:0,0` recommendation) live.

### `alsa-plugins` 1.2.12 — the converters the config avoids

`alsa-plugins` supplies the additional PCM and rate-converter plugins — `samplerate` (via libsamplerate), `speexrate` (via libspeex) and `lavrate` (via FFmpeg). These are exactly the floating-point-heavy converters that the `alsa-lib` configuration steers around on FPU-less targets; they are present for completeness and for capable hardware, but are not on the default music path.

### `alsa-utils` 1.2.13 — the command-line toolbox and its build options

`alsa-utils` is the core command-line toolset for exercising and debugging the sound stack. It depends on `alsa-lib`, and selecting it auto-selects the USB-audio kernel stack so a DAC comes up cleanly. At the always-present level it provides `aplay` and `arecord` (playback and capture), `amixer` and `alsactl` (mixer and state control), `speaker-test`, and MIDI/sequencer utilities. Beyond those, the `make menuconfig` tree for `alsa-utils` exposes a set of optional components, each of which can be built in or left out:

- **`alsamixer` (ncurses UI)** — the interactive full-screen mixer: a terminal UI for setting playback/capture levels, muting, and switching between cards and views (playback / capture / all). On a USB DAC this is the quickest way to see and set the hardware's own mixer controls.
- **`alsaconf`** — the interactive sound-card configuration script, used to detect a card and write a starting ALSA configuration.
- **`alsaloop`** — a PCM loopback tool that pipes a capture device into a playback device in real time; useful for routing an input to the DAC output and for latency/return testing.
- **`alsabat` and the bat helpers** — the "Basic Audio Tester": it generates a test signal, plays it, captures it back and runs frequency analysis (FFT), giving an automated pass/fail audio test of the whole capture-and-playback path.
- **NHLT tools** — utilities for reading/parsing the Non-HD-Audio Link Table (the ACPI table that describes non-HDA endpoints such as digital microphones), for inspecting how audio endpoints are declared on a platform.

### The `alsa-utils` CGI — an audio status and test web UI

A Freetz-EVO specific addition to `alsa-utils` is its **CGI web interface**, selectable in `make menuconfig` as *"alsa-utils CGI (audio status/test web UI)."* This brings the command-line capabilities into the FRITZ!Box web interface: from a browser the user can inspect and control the **ALSA configuration and the USB-interconnected DAC components** — reading the current card/PCM state, adjusting mixer controls, and running playback/record tests — without opening an SSH session. It is the graphical front-door to the same functionality that `aplay -l`, `amixer`, `speaker-test` and friends provide on the command line, and it is the natural companion to the USB-DAC-centric hardware model, since it lets the ALSA-visible controls of an attached DAC be driven from the web UI.

### `alsaequal` 0.7.1 (DEVELOPER) and the CAPS LADSPA suite

As discussed before, `alsaequal` bridges a LADSPA equalizer into ALSA's PCM/ctl device model. It ships the two bridge modules (`libasound_module_pcm_equal.so` and `libasound_module_ctl_equal.so`) and selects the **CAPS LADSPA** plugin suite by default, so the ten-band `Eq10` module is available out of the box; a different compatible LADSPA equalizer can be configured at runtime. The broader **CAPS (Computer Audio Processing Systems) LADSPA suite** itself provides a whole family of audio effects — amplifiers, equalizers, delays, reverbs and modulation effects — and is the DSP back-end that `alsaequal` plugs into ALSA. Because of the FPU cost, `alsaequal` is developer-mode/disabled by default, and the practical equalization path is the DAC's hardware DSP instead. Where the optional `alsaequal-cgi` is built, it adds persistent equalizer settings, generated ALSA snippets and runtime control from the web UI (config at `/cgi-bin/conf/alsaequal`, status at `/cgi-bin/status/alsaequal`), integrating with `amixer` for live control of the exported equalizer controls.

---

## The MPD ecosystem — the heart of local and networked playback

The richest cluster of audio applications in Freetz-EVO is built around **MPD, the Music Player Daemon**. MPD is a server: it runs as a daemon, maintains a music database, exposes a control protocol on TCP port 6600 (and a local UNIX socket at `/var/run/mpd/socket`), decodes audio and pushes PCM to an output. Everything else in this section — command-line, terminal-UI, web-UI and the exclusive web-radio front-end — is a *client* that drives that daemon over its protocol. This client/server split is what lets the FRITZ!Box behave as an always-on music appliance that can be controlled from a browser, a phone, a terminal, or a shell script, all at once.

### MPD 0.24.13 — the engine and its decoder/output matrix

MPD provides `/usr/bin/mpd` and links against `alsa-lib`, `flac`, `libid3tag`, `libmad`, `libogg`, `libvorbis` and `zlib`. In its Freetz-EVO default posture it is trimmed for embedded use — the local music database, TCP + UNIX-socket control, daemon mode with inotify monitoring, ALSA output, MP3 (libmad), FLAC, Ogg/Vorbis and libcurl HTTP/HTTPS input are on by default, while heavier options are opt-in. What makes MPD remarkable here is the breadth of decoders, encoders, inputs and outputs that `make menuconfig` lets you switch on. Each toggle maps to a concrete musical capability:

| `menuconfig` option | What it enables |
|---|---|
| Remote URI input (libcurl) | Fetch/stream remote `http(s)://` resources — the backbone of **web-radio** playback and remote playlists |
| SQLite database plugin | Store the song/tag database (and stickers: ratings, play counts) in SQLite |
| bzip2 compressed playlist/archive | Read songs out of `.bz2` archives and compressed playlists |
| FFmpeg decoder integration | Universal decoder — adds AAC, ALAC, WMA, APE, TTA and many container audio tracks |
| WavPack decoder | Play `.wv` lossless/hybrid WavPack files |
| UPnP Media Server | Consume DLNA/UPnP media servers as a database source |
| Expat XML parser | XML parsing for UPnP/SOAP and some playlist formats |
| Opus decoder | Decode Opus (efficient modern codec, common on web radio) |
| iconv charset conversion | Convert non-UTF-8 tag charsets for correct display |
| Vorbis encoder | Re-encode output to Ogg Vorbis for streaming outputs |
| IPv6 | Serve control and streams over IPv6 |
| DSD support | Native DSD (`.dsf` / `.dff`, SACD-style 1-bit) playback |
| CUE sheet support | Treat one image + `.cue` as separate indexed tracks |
| UPnP neighbor discovery | Auto-discover UPnP servers on the LAN |
| WebDAV input | Stream files from WebDAV shares |
| Named pipe output | Write PCM to a named pipe for external processing |
| FIFO output | Classic FIFO output (feeds visualizers) |
| HTTP daemon output | MPD serves its own audio as an HTTP stream (a mini Icecast) |
| FAAD2 (AAC) decoder | Decode AAC / `.m4a` via FAAD2 |
| FluidSynth (MIDI) decoder | Render `.mid` MIDI through a SoundFont |
| libsamplerate (SRC) output | High-quality "Secret Rabbit Code" resampling |
| mpg123 (MP3) decoder | Alternative MP3 decoder to libmad |
| NFS input | Read music directly from NFS shares |
| shine (MP3) encoder | Fixed-point MP3 **encoder** — ideal for streaming on FPU-less targets |
| Icecast (shout) output | Stream MPD output to an Icecast/Shoutcast server |
| libsoxr (SRC) output | SoX resampler — very high-quality rate conversion |
| Tremor (low-memory Vorbis) decoder | Integer-only Vorbis decoder for low-resource CPUs |
| WildMIDI decoder | Alternative GUS-patch-based MIDI renderer |
| MPD CGI (config/status web UI) | Builds the `mpd-cgi` package: web configuration of `mpd.conf`, daemon start/stop and a live status page in the Freetz-EVO WebIF |

Two of these deserve a note in the context of the previous section: the **shine** encoder and the **Tremor** decoder are both fixed-point (integer) implementations, chosen precisely so that MP3 encoding and Vorbis decoding can run without the FPU. The `libsoxr` / `libsamplerate` outputs exist for completeness but belong to the same "avoid on soft-float" category as the ALSA converters.

### `libmpdclient` 2.22 — the shared client library

`libmpdclient` provides `libmpdclient.so.2`, the official MPD client library that `mpc`, `ncmpc` and `ncmpcpp` all link against (myMPD embeds its own copy). Its Freetz-EVO defaults are tuned for the box: clients auto-connect to localhost on TCP 6600 and to the UNIX socket `/var/run/mpd/socket` unless told otherwise — which is exactly why the exclusive web-radio front-end (see subsequently) can default to the socket and simply work.

### `mpc` 0.35 — the command-line client

`mpc` is the lightweight, shell-friendly MPD client: status queries, play/pause/toggle/stop, next/prev/seek, queue edits (`add` / `del` / `move` / `shuffle` / `clear`), playlist browsing (`load` / `playlist` / `lsplaylists`), volume and playback modes, with `--host` (host, `password@host`, or socket path), `--port` and `--partition`. It is ideal for scripts, cron jobs and SSH sessions — and, importantly, it is the binary on top of which the exclusive web-radio CGI is built: every button in that web UI ultimately shells out to `mpc`.

### myMPD 25.0.2 — the modern standalone web client

`myMPD` provides `/usr/bin/mympd`, a self-contained daemon with embedded web assets and an embedded copy of libmpdclient. It serves a full, responsive single-page browser control surface directly from the box over HTTP or HTTPS — a modern, phone-friendly UI for browsing the library, managing the queue and playlists, viewing album art and controlling playback, with no external front-end required. An optional `mympd-cgi` package wires its configuration and status into the Freetz-EVO web interface (`/cgi-bin/conf/mympd`, `/cgi-bin/status/mympd`). It is worth noting that myMPD comes from **jcorporation**, the same author as the WebRadioDB database that the exclusive web-radio front-end consumes.

### `ncmpc` 0.52 — the official ncurses TUI

`ncmpc` is the official terminal client, depending on `libmpdclient` and `ncursesw`. It presents a full ncurses interface with screens for help, the library, search, the current song, key-bindings, outputs and lyrics; it lets you browse the library, edit the queue/playlist, search, view lyrics and control playback, with colours and mouse support. Its optional features map to the `make menuconfig` toggles: **iconv** (charset conversion for non-UTF-8 tags), **PCRE2** (regex search), **NLS/gettext** (localized messages) and **LIRC** (infrared-remote control via `liblirc_client`) — the last being a nice touch for a living-room appliance driven by a remote.

### `ncmpcpp` 0.9.2 — the feature-rich TUI

`ncmpcpp`, the C++ successor to ncmpc, extends it with a **tag editor**, a **media-library browser**, advanced playlist management, search, a clock display, a configurable outputs screen and a **built-in audio visualizer** (spectrum/wave, typically fed from an MPD FIFO output). It depends on `libmpdclient`, `ncursesw`, `curl` and `taglib`. It is the most fully featured of the terminal MPD clients and, like the others, can drive either the local MPD or any reachable MPD on the network.

### ⭐ The exclusive `mpd-mpc` CGI — "mpc Web Radio"

This is the centrepiece of the MPD ecosystem and a **Freetz-EVO original**, with no upstream equivalent. In `make menuconfig`, it appears as *"mpc CGI (MPD CLI radio control web UI)"*. The application turns MPD into a point-and-click **continuous music and internet radio appliance**: users can assemble and play **local playlists**, browse a large catalogue of **internet radio stations**, or create a **mixed queue containing both**, with full playback control and automatic playback at boot.

Three Freetz-EVO web interface menu items are relevant:

- **"MPD"** — the MPD service must be started first;
- **"Status" > "mpc Web Radio"** — the main interface for controlling playback;
- **"mpc Web Radio"** — configuration options, including automatic playback at boot.

The `mpd-mpc` CGI provides a browser-based, always-on music and internet radio appliance. It combines locally stored music with a large curated catalogue of internet radio stations and supports advanced playback features such as gapless playback, crossfade, MixRamp, and ReplayGain. It also supports automatic resume/playback at boot. The application is implemented as a shell script that communicates with MPD through `mpc` and integrates directly with the [WebRadioDB project](https://jcorporation.github.io/webradiodb/).

All settings can be managed through the web interface, including playlists, internet radio stations, playback controls, and transition and loudness-processing features such as **crossfade, MixRamp dB/delay, and ReplayGain**.

With just a few clicks, users can configure a fully unattended continuous internet radio or music playback system: enable automatic startup for both **MPD** and **mpc Web Radio**, then go to **"Status" > "mpc Web Radio"**, select a radio station or local playlist, and press **Play**.

**The live UI.** The `status.cgi` page renders a dashboard organised into eleven sections that together deliver the "define locally or choose from the web" experience:

1. **Live overview** — a status table (configured vs. active MPD target, partition, autoplay flag, saved station, current title/artist/year/station, on-air time range, duration, metadata source/ID, current URI, player state, elapsed/total progress, queue position/length, volume, station homepage) plus an **artwork card** that extracts embedded album art (via `mpc albumart` / `mpc readpicture`), sniffs its type from the magic bytes and shows it inline as a `data:` URI.
2. **MPD controls** — transport buttons (play, pause, toggle, stop; prev / −10 s / +10 s / next when a finite timeline exists; current, status, shuffle queue, clear queue), a live volume slider with 0/25/50/75/100 % presets, and a refresh/setup row (auto-refresh, sync WebRadioDB, disable autoplay, jump to configuration).
3. **Transitions & effects** — the "continuous diffusion" polish, applied live and persisted: a **crossfade** slider (0–30 s), **MixRamp** dB and delay sliders (overlap tracks by loudness rather than silence), a **ReplayGain** selector (off/track/album/auto), and the **repeat / random / single / consume** playback-mode toggles.
4. **Queue management** — the mixed local+web queue, paginated and client-side searchable, with per-row play / move-up / move-down / delete and toolbar shuffle/clear. This is where local files and web radios are interleaved and reordered into one continuous programme.
5. **Local file browser** — browses directories under the configured root (with traversal guarded), and can queue a single file or, with "+ Dir", recursively enqueue every audio file in a folder (mp3/flac/ogg/wav/m4a/aac/wma/opus/ape/wv/aiff/dsf/dff). It correctly strips the music-directory prefix so paths are MPD-database-relative.
6. **Local playlists** — save the current queue as a named `.m3u` in the playlist directory, list existing playlists, load one (replacing the queue), or delete one. This is the surface for **defining a local diffusion**: build a queue, save it, recall it later, or pin it as the boot station.
7. **Command output** — a console echoing the last action's exact `mpc` command and its output, for transparency and debugging.
8. **Manual station** — a form (name, stream URI, image, homepage) with "Queue", "Play now" and "Save startup" buttons, to add any arbitrary stream or local URI and optionally pin it as the always-on station.
9. **WebRadioDB browser** — the marquee feature: a searchable catalogue UI over **jcorporation's WebRadioDB** (`webradiodb-combined.min.json`, thousands of curated stations with artwork). The CGI caches the JSON server-side; the client offers a full-text search box plus **Country / Language / Genre / Codec** filter dropdowns auto-populated from the data, renders up to sixty station cards (image, name, description and up to seven tags for country/region/codec/bitrate/languages/genres), and gives each station "Queue / Play now / Save startup" actions. Station identity is passed to the backend base64url-encoded so arbitrary UTF-8 names and URLs survive the round-trip. This is how the user **chooses a station from the web** and one-clicks it into the programme.
10. **Raw MPD output** — a verbatim `mpc status` / `current` dump for diagnostics.
11. **Autoplay log** — the last lines of the boot autoplay log, so power-on behaviour is visible in the UI.

Technically, `mpd-mpc` is a pure POSIX-shell CGI — no PHP, no server-side runtime, nothing beyond `mpc` and `wget`. Its source lives at `make/pkgs/mpd-mpc-cgi/` and its live UI (`status.cgi`) is a single ~100 KB shell script. Persistent settings live in `/mod/etc/conf/mpd-mpc.cfg`. They cover the MPD connection (host or UNIX socket — with automatic fallback to `/var/run/mpd/socket` when a loopback host is given — port, partition, password), the WebRadioDB source URL and cache directory, the local-file browser root (default `/var/media/ftp`), the playlist directory, the MPD music directory (auto-detected from `mpd.conf` if unset), and the transition effects. The init script `rc.mpd-mpc` registers the CGI and, if a startup station/playlist has been saved and autoplay is enabled, waits up to a configurable number of seconds for MPD to answer, then stops, optionally clears the queue, adds the saved URI, applies the volume and the crossfade/MixRamp/ReplayGain settings, and starts playback — logging to `/tmp/rc.mpd-mpc.log`. This is what makes the box resume a chosen web station or local playlist automatically at power-on, with no interaction. The source of `mpd-mpc` CGI is at [`mpd-mpc.cgi`](https://github.com/Ircama/freetz-evo/blob/master/make/pkgs/mpd-mpc-cgi/files/root/usr/lib/cgi-bin/mpd-mpc.cgi).

---

## Streaming and casting receivers

Alongside the MPD "player-on-the-box" model, Freetz-EVO ships three receivers that let external devices push audio *to* the FRITZ!Box device, turning it into an endpoint on the home network. All three output through ALSA to the attached USB DAC.

### go-librespot 0.7.1 — a Spotify Connect endpoint

`go-librespot` is an open-source Go reimplementation of Spotify's `librespot` that makes the FRITZ!Box appear on the LAN as a **Spotify Connect** device: any Spotify app on a phone or desktop can select the box as its playback target and stream to it, with playback and control handled on the box. It is provided as `/usr/bin/go-librespot` and depends on `alsa-lib`, `flac`, `libogg` and `libvorbis`. The package is a **target-native Go build with CGO enabled**, so the daemon talks directly to the target's ALSA and codec libraries rather than pure-Go audio; the enabled stack is ALSA playback plus FLAC and Ogg/Vorbis (Spotify's native stream format). Selecting it auto-selects the exposed ALSA USB audio driver stack, so USB-DAC playback works without manual module hunting.

Its **CGI web UI** — selectable as *"go-librespot CGI (Spotify Connect config/status web UI)"* — configures the daemon from the Freetz-EVO web interface, generating go-librespot's YAML configuration at runtime, offering daemon start/stop control and a live status page, with generated configuration persisted under `/mod/etc/default.go-librespot/` (config at `/cgi-bin/conf/go-librespot`, status at `/cgi-bin/status/go-librespot`).

### shairport-sync 5.0.4 — an AirPlay receiver

`shairport-sync` turns the box into an **AirPlay audio receiver** with ALSA output. It provides `/usr/bin/shairport-sync` and a small `shairport-sync-status-cache` helper, and depends on `alsa-lib`, `libconfig`, `libdaemon`, `popt` and `libssl`. The Freetz-EVO build is trimmed to the embedded case: the ALSA output backend, OpenSSL for the AirPlay handshake, metadata support and a bundled tiny mDNS/Zeroconf responder (`tinysvcmdns`) so the device advertises the AirPlay service by itself without Avahi. Its signature capability is precise **audio-clock synchronization** — it keeps playback time-aligned with the sender — and it exposes track metadata (title, artist, album, client, playback state) through a metadata FIFO that a reader feeds to the live status page. (The trimmed dependency set — without the nqptp/libplist/ffmpeg/libsodium companions that AirPlay 2 requires — indicates a classic single-stream AirPlay-1 receiver build.)

Its **CGI** — *"shairport-sync CGI (AirPlay config/status web UI)"* — provides `/usr/lib/cgi-bin/shairport-sync.cgi` and a status CGI: a configuration page for the AirPlay and ALSA settings, an init script with daemon registration and metadata-collector management, and a status page that consumes the cached metadata FIFO output to show the active client, playback state, track metadata and recent logs.

### snapcast 0.35.0 — synchronized multi-room audio

`snapcast` is a **multi-room audio distribution system**: a central **snapserver** reads an audio stream and broadcasts it with embedded timing to any number of **snapclient** receivers, which use that timing to play in perfect, drift-free sync across rooms — whole-home audio with no echo between zones. Both binaries (`snapserver` and `snapclient`) ship in the one package, so a single box can be server, client, or both; a default `/etc/snapserver.conf` and shared assets under `/usr/share/snapserver` are installed. It depends on `alsa-lib`, `flac`, `libogg`, `libvorbis` and `openssl`, with the ALSA output backend and FLAC/Ogg-Vorbis stream codecs enabled (heavier Avahi/Opus/PulseAudio/JACK/PipeWire options are left out to keep the footprint small). Snapcast does not itself produce audio: the standard pattern is to point a player such as MPD (or an AirPlay/Spotify receiver) at a named pipe that snapserver reads as its source, and snapserver then fans that stream out to all clients — which is exactly how it slots in beside the rest of this subsystem. Its **CGI** is selectable as *"snapcast CGI (Snapserver/snapclient config/status web UI)"* for configuring the server and client and viewing their status from the web interface.

---

## The terminal-UI player family

Freetz-EVO includes several useful **TUI (text/terminal user interface) applications** for audio. Since the box is typically headless and accessed over SSH, these ncurses/terminal applications provide a practical way to browse music libraries and control playback directly on the device. In addition to the MPD TUIs already described (`ncmpc`, `ncmpcpp`), three more are worth mentioning.

### cmus 2.11.0 — the local ncurses player

`cmus` (C\* Music Player) is a self-contained **local** player: unlike the MPD clients, it decodes and plays files on the device itself. It provides `/usr/bin/cmus` and `/usr/bin/cmus-remote` and depends on `alsa-lib`, `libatomic`, `ncursesw`, `libmad`, `FLAC` and `libvorbisfile` — an ALSA-out, fixed-point-codec stack (`libmad` MP3 decode is integer-only, ideal for FPU-less MIPS). Its TUI is organised into numbered views switched with keys `1`–`7` (library tree, sorted library, playlist, play queue, file browser, filters, settings/keybindings), with vi-style navigation and incremental search (`/`, `?`), a `:` command mode for everything, live library filtering, gapless playback, ReplayGain, fully rebindable keys and colour themes. The bundled `cmus-remote` controls a running instance over IPC — perfect for scripting or driving playback from another shell. It auto-selects the USB audio kernel stack, so it is a natural fit for USB-DAC playback of locally stored or USB-mounted music.

### ncspot 1.3.4 — a Spotify client in the terminal

`ncspot` is a lightweight **terminal Spotify client** built on librespot, explicitly inspired by `ncmpc` and `cmus`. It provides `/usr/bin/ncspot`, is a Rust/Cargo cross-build depending on `rust-host`, `openssl` and `alsa-lib`, and is compiled with just the `alsa_backend` and `crossterm_backend` features (desktop/DBus/notification integrations stripped for the embedded target). As a TUI it offers distinct panes for the play queue, search, library (saved tracks/albums/artists) and playlists; full-text search across tracks/albums/artists/playlists; library and discography browsing; vim-style navigation with a `:` command prompt; configurable keybindings and theming; keyboard playback control (play/pause, next/prev, seek, shuffle, repeat, volume, add-to-queue/playlist); and a persistent now-playing status bar. It needs a Spotify Premium account and sends audio out via ALSA — an excellent way to drive Spotify entirely over an SSH session.

### rmpc 0.11.0 — a modern MPD TUI

`rmpc` is a "beautiful, configurable" Rust TUI client for MPD (`/usr/bin/rmpc`, depending on `rust-host`). It is one of the most visually modern MPD front-ends: it renders **in-terminal album artwork** (via modern terminal graphics protocols such as Kitty/iTerm/sixel, with a text fallback), shows **synced lyrics**, manages the queue and playlists, browses the library by tag (artist/album/genre) or directory, offers search/filtering and full playback control, is highly configurable (config file, custom keybindings, themeable tabbed layout) and — unusually for a TUI — supports **mouse interaction**. As a pure MPD client it pairs with the local `mpd` package or controls any reachable MPD, and is ideal for interactive SSH use.

---

## SoX 14.4.2 — the audio-processing Swiss Army knife

`SoX` (Sound eXchange) is the command-line utility for **converting, playing and recording** audio, with a large effects library. It can transcode among all the mainstream music formats and several speech codecs, read MP3 tags, apply its full effects and resampling suite, record and play through ALSA, and produce spectrograms.

More in detail, it installs `sox` plus `play` and `rec` (symlinks to `sox`; SoX changes behaviour based on the name it is invoked as). It performs format conversion/transcoding (changing container, codec, sample rate, bit depth and channel count in one command), playback and capture (`play file`, `rec file`), high-quality resampling (with the companion `soxr` package for the SoX Resampler library), a full effects chain (trim, fade, gain/normalize, bass/treble/equalizer, reverb, echo/chorus/flanger/phaser/tremolo, pitch/tempo/speed, silence detection, noise profiling/reduction, remix/channel mapping, dither and `stat`/`stats` analysis), tone/waveform **synthesis** (the `synth` effect), and **PNG spectrogram** rendering.

The project's documentation ships a `tones.sh` example that uses SoX's `synth` mode to generate a 20 Hz–20 kHz sweep straight to ALSA (`hw:0,0`, 48 kHz, S16, stereo) to verify DAC output across the frequency range.

The `make menuconfig` options selected for the SoX package determine which formats and features it understands:

| Enabled option | Meaning |
|---|---|
| libsndfile (WAV/AIFF/FLAC/CAF) | General soundfile library — robust read/write of WAV, AIFF, FLAC and Apple CAF containers |
| MP3 support | Read (libmad) and write (LAME) MPEG-1/2 Layer III `.mp3` |
| Og0g Vorbis support | Read/write the open lossy `.ogg` Vorbis codec |
| FLAC support | Read/write the Free Lossless Audio Codec `.flac` |
| WavPack support | Read/write the hybrid lossless/lossy WavPack `.wv` |
| Opus support | Read/write the modern low-latency `.opus` codec |
| GSM support | GSM 06.10 full-rate (~13 kbit/s) telephony speech codec |
| PNG spectrogram output | The `spectrogram` effect emits a PNG frequency-vs-time image (libpng) |
| ID3 tag support | Read ID3 metadata (title/artist/album) from MP3s (libid3tag) |
| libgooglevoice8 (G.728) | The ITU-T G.728 Low-Delay CELP 16 kbit/s narrowband speech codec |

---

## ⭐ The exclusive USB-DAC configuration layer — HID, WebSockets and the JA11

This is an important part of Freetz-EVO's audio functionality and addresses the FPU limitation described above: rather than performing equalization and filtering on the CPU of the FRITZ!Box device, the project provides tools to configure a **hardware-DSP USB DAC** directly, allowing the processing to be performed by the DAC.

The functionality is provided through three components: a **generic** HID-over-WebSocket gateway that can support multiple DACs, a **Python 3 hidapi library** for direct HID access from Python3 applications, and a **device-specific** toolset for the FiiO/JadeAudio **JA11**.

### Broad DAC support, "depending on kernel features" — the two hidapi backends

The breadth of supported DACs is governed by **`hidapi` 0.15.0**, which lets applications talk to USB/Bluetooth HID-class devices and is built here with two backends:

- **libusb backend** (`libhidapi-libusb.so`) — talks to the kernel's `usbfs` interface directly and **does not require the kernel HID/INPUT subsystem**, which matters because GRX5 devices (e.g. the 7590AX) ship an AVM kernel without `CONFIG_INPUT`. This is the universal fallback and the backend that the tools below use.
- **hidraw backend** (`libhidapi-hidraw.so`) — talks to the kernel `hidraw` interface and auto-selects `hid.ko` / `hid-generic.ko` / `usbhid.ko`, but depends on the kernel providing INPUT/HID and is explicitly **not compatible with GRX5** (where `hid.ko` cannot load for lack of `input_allocate_device`).

Where the AVM kernel offers INPUT/HID, generic hidraw-based access is available; everywhere else, the libusb/usbfs path still allows HID DAC configuration. On top of that generic support, the JA11 gets special, dedicated functions.

### `hidws` 1.3.1 — HID/WebSocket gateway

`hidws` is a WebSocket-to-HID bridge. It uses libwebsockets for the WebSocket server and hidapi with the libusb backend for HID access, so it can also work on FRITZ!Box devices where the kernel HID/INPUT subsystem is unavailable, such as GRX5 models.

It optionally supports authentication and TLS/WSS, and provides a companion diagnostic binary, **`hid-list`**, which enumerates USB HID devices and the reports they support.

The gateway also provides a web-based diagnostic page over HTTP/HTTPS on the same port. Opening `http://<host>:<port>/` or `https://<host>:<port>/` in a browser confirms that the daemon is reachable and displays its version, port, and available WebSocket endpoints. The **Test ws://** and **Test wss://** buttons open a real WebSocket connection to the server and report whether it succeeds or fails.

When a temporary in-memory certificate is being used, the page displays a warning banner.

For WSS connections, this page also provides a convenient way to accept the browser's one-time security exception for the self-signed certificate: visit `https://192.168.178.1:9001/`, accept the certificate warning, reload the page, and press **Test wss://**.

### `hidws-cgi` — the web page and its launcher of modified web apps

The `hidws-cgi` package is the Freetz web-interface front-end for the gateway. It renders the service configuration (enable/disable, WebSocket port, process priority, SSL on/off, certificate and key paths, the optional client credentials, shows whether the daemon is running (`pgrep -x hidws`), advertises both the `ws://` and `wss://` endpoints, and tails the startup and daemon logs (`/tmp/rc.hidws.log`, `/tmp/hidws.log`).

It is also a **launcher of advanced web applications** that have each been modified to connect back to the local `hidws` over WebSocket and configure the attached DAC in real time. The CGI links the following apps, all rehosted under GitHub Pages so they talk to the box:

| App | URL | Role |
|---|---|---|
| ⭐ fiiocontrol | <https://ircama.github.io/fiiocontrol/> | The **modified native FiiO Control** web app (equalizer / custom tuning) — the flagship reference |
| kt02h20-control | <https://ircama.github.io/kt02h20-control/> | Control for the FiiO JA11 (KT02H20 chip) |
| Audiocular-Aura (AuraPEQ) | <https://ircama.github.io/Audiocular-Aura/> | Parametric equalizer for USB DACs (the upstream project the whole layer is based on) |
| fiiocontrol-oss | <https://ircama.github.io/fiiocontrol-oss/> | Open-source EQ control for FiiO DACs |
| webhid-explorer | <https://ircama.github.io/webhid-explorer/> | HID explorer (devices, report descriptors) |
| ⭐ walkplay | <https://ircama.github.io/walkplay/> | Offline build of the official WalkPlay PEQ app, including enhancements |

The first **fiiocontrol** web app is the reference for FiiO JA11.

The latest **walkplay** web app allows configuring the **Hi-MAX Audio (TTGK Technology) CB1200AU** DAC (8-band parametric EQ (±10 dB), DAC filters and firmware info). It works without a WalkPlay account (login is optional, only to pull online EQ presets).

### `ja11-config` — firmware update and an advanced PEQ/filter/gain TUI for the JA11

The **`ja11-config`** toolset provides configuration and firmware-management utilities for the **FiiO JadeAudio JA11** USB DAC/Amp and other devices based on the **KT Micro KT02H20** DSP chip, including the JKALLY JM12 and native KTMicro dongles.

The main utility, **`ja11-config-tui`**, is an interactive text-based user interface (TUI) for configuring the device over HID. It provides access to a 5-band parametric equalizer (PEQ), DAC digital filters, and global preamp gain, with settings that can be saved persistently to flash.

Firmware updates are handled by **`ja11-boot`**, which switches the device to firmware-update (boot) mode. The device then re-enumerates as a USB CDC virtual serial port, which is used by **`ja11-flash`** to transfer the new firmware.

Through these applications, users can flash firmware directly from the box and perform comprehensive, real-time configuration of the DAC through an efficient user interface.

The updater works in two stages: `ja11-boot` sends a specific HID output report that puts the DAC into bootloader mode, whereupon it re-enumerates as a **USB CDC-ACM serial device** (e.g. `/dev/ttyACM1`); then `ja11-flash /dev/ttyACM1 fw.bin` writes the new firmware over that serial port.

Because the JKally JM12 is built on the same KT02H20 chip, a JM12 can be **cross-flashed with FiiO's JadeAudio JA11 firmware (v2.2)** using these tools; once it runs JA11 v2.2 it is indistinguishable from a genuine JA11 for configuration purposes — most notably, it becomes usable with the native FiiO Control app.

**The `ja11-config-tui` configurator.** is internationalized in **five languages** (English, Italian, French, German, Spanish, selectable by CLI flag). Its capabilities:

- A **5-band parametric equalizer**. Each band has an on/off state, a frequency (20–20000 Hz), a gain (−24 to +12 dB), a Q (0.1–10.0) and a filter type — **PK** (peaking), **LSQ** (low-shelf) or **HSQ** (high-shelf). Default band centres are 100 / 500 / 1000 / 2500 / 10000 Hz at Q 0.7.
- A **global preamp gain** (−12 to +12 dB). The protocol layer additionally defines a balance range (−15…+15), an amplifier-mode command (Class H / AB) and a gain-mode command (Low / High), but these remain defined constants in the code rather than interactive controls in the current TUI — the only directly editable "strip" parameters are the global preamp gain and the DAC digital filter.
- **Five selectable DAC digital filters**: `FAST-LL` (fast roll-off, linear phase, low latency — the default), `FAST-PC` (fast roll-off, phase compensated), `Slow-LL` (slow roll-off, linear phase), `Slow-PC` (slow roll-off, phase compensated) and `NON-OS` (non-oversampling).
- **Presets** — up to sixteen named presets (each storing the five bands plus global gain), saved to a preset file (default `/tmp/ja11-presets.conf`).
- A live **HID traffic log** for diagnostics.

The on-screen layout is a title/connection bar, an editable status strip showing the global preamp and the DAC digital filter, and a band table with columns Band / Freq / Gain / Q / Type / Status, together with a "modifications not applied" indicator and a quit guard against losing unsaved edits.

### `python3-hidapi` and the KTMicro tooling

Because `hidapi` is present on the box, Freetz-EVO also ships **`python3-hidapi`** — the Python `hid` / `hidapi` binding that links against the same `libhidapi`. With Python 3 and this binding on the box, pure-Python HID tools run directly on the device. The one that matters here is [`Ircama/ktmicro-tools`, branch `add-libusb-backend-and-ja11-support`](https://github.com/Ircama/ktmicro-tools/tree/add-libusb-backend-and-ja11-support), derived from [`gxcreator/ktmicro-tools`](https://github.com/gxcreator/ktmicro-tools). The fork adds a **libusb backend** — so it reaches the DAC through `usbfs` on kernels without `hidraw`, and adds support for the **FiiO/JadeAudio JA11 (VID `0x2972`) alongside the KT02H20**.

### Tested devices

The USB-DAC layer has been exercised against three concrete devices, each a USB Audio Class DAC that also exposes an HID configuration interface. All three deliver up to 32-bit / 384 kHz playback; they differ in DSP capability and, consequently, in which tools configure them:

| Device                                         | VID      | PID      | DAC / DSP chip | Configuration DSP            | Configured with                                                                                                         |
| ---------------------------------------------- | -------- | -------- | -------------- | ---------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| **Hi-MAX Audio "walk play"** (TTGK Technology) | `0x3302` | `0x12CA` | CB1200AU       | 8-band parametric EQ, ±10 dB | **walkplay** (Dongguan Hengmin Electronic Technology Co., Ltd.) |
| **JCALLY JM12**                                | `0x31b2` | `0x0111` | KT02H20        | 5-band parametric EQ, ±12 dB | **ja11-config-tui**, plus **kt02h20-control**, **Audiocular-Aura**, **fiiocontrol-oss**                                 |
| **FiiO/JadeAudio JA11**                        | `0x2972` | `0x0102` | KT02H20        | 5-band parametric EQ, ±12 dB | **ja11-config-tui**, **fiiocontrol** (firmware 2.2), plus **kt02h20-control**, **Audiocular-Aura**, **fiiocontrol-oss** |

The two KT02H20 devices are effectively the same hardware. A **JCALLY JM12 can be turned into a JA11** by cross-flashing FiiO's JadeAudio JA11 firmware v2.2 with the `ja11-config` tools (`ja11-boot` + `ja11-flash`); the firmware image is published by FiiO ([JadeAudio JA11 Firmware V2.2](https://fiio-firmware.fiio.net/JA11/%E8%8B%B1%E6%96%87%E5%9B%BA%E4%BB%B6/JadeAudio%20JA11%20Firmware%20V2.2.zip)). Both a native JM12 and a genuine JA11 are configured by the `ja11-config-tui` ncurses application on the box, and by the `kt02h20-control`, `Audiocular-Aura` and `fiiocontrol-oss` web apps over `hidws`. The one tool with a firmware precondition is the **native FiiO Control app (`fiiocontrol`)**: it works only once the device is running **JA11 firmware 2.2**. The Hi-MAX Audio "walk play" is a different chip (CB1200AU) and is configured exclusively through the **walkplay** app.
