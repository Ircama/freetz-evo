# Welcome to Freetz-EVO

<div class="evo-home" markdown="1">

<section class="evo-hero" markdown="1">
<div class="evo-hero__copy" markdown="1">

**Freetz-EVO** is an actively synchronized fork of [Freetz-NG](https://github.com/Freetz-NG/freetz-ng) for building enhanced firmware images for AVM FRITZ!Box devices. It keeps Freetz-NG as the technical base while adding EVO-only packages, package fixes, a responsive web interface, hardened session login, reverse-proxy tooling, and stronger build/test workflows.

Compared with Freetz-NG, this tree adds **199+ package makefiles** and **71+ libraries**, modifies **33+ packages** and **50+ libraries**, and carries substantial documentation and tooling work.

<p class="evo-actions" markdown="1">
[Repository README](REPO_README.md){ .evo-button .evo-button--primary }
[Build an image](GETTING_STARTED.md){ .evo-button }
[Try the UI mockup](screenshots/evo-demo.html){ .evo-button }
</p>
</div>

<div class="evo-hero__panel" aria-label="Freetz-EVO identity">
  <img src="screenshots/000-TAG_freetz-evo.png" alt="Freetz-EVO logo" class="evo-logo">
  <div class="evo-terminal-card" data-evo-terminal>
    <span class="evo-terminal-card__bar">
      <button type="button" class="evo-terminal-card__expand" data-evo-terminal-toggle aria-expanded="false" aria-controls="evo-terminal-commands" aria-label="Expand command list" title="Expand command list"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/></svg></button>
    </span>
    <span class="evo-terminal-card__lines" id="evo-terminal-commands" aria-hidden="true">
    <span><span class="evo-terminal-card__prompt">&gt;&nbsp;</span>git clone https://github.com/Ircama/freetz-evo</span>
    <span><span class="evo-terminal-card__prompt">&gt;&nbsp;</span>cd freetz-evo</span>
    <span><span class="evo-terminal-card__prompt">&gt;&nbsp;</span>tools/prerequisites install -y</span>
    <span><span class="evo-terminal-card__prompt">&gt;&nbsp;</span>make menuconfig</span>
    <span><span class="evo-terminal-card__prompt">&gt;&nbsp;</span>make</span>
    <span><span class="evo-terminal-card__prompt">&gt;&nbsp;</span>tools/push_firmware</span>
    <span><span class="evo-terminal-card__prompt">&gt;&nbsp;</span>tools/ssh_firmware_update.py --host &lt;myIP&gt; --password &lt;myPassword&gt; --batch</span>
    </span>
  </div>
</div>
</section>

<section class="evo-section" markdown="1">
## Start Here

<div class="evo-card-grid" markdown="1">
<div class="evo-card" markdown="1">
<strong class="evo-card__title">Build Safely</strong>

Set up the host, configure the image, build it, and flash with the documented workflow.

[Prerequisites](prerequisites/README.md) &middot; [Getting Started](GETTING_STARTED.md) &middot; [Install](INSTALL.md)
</div>
<div class="evo-card" markdown="1">
<strong class="evo-card__title">Check Compatibility</strong>

Review supported firmware and device information before selecting packages or flashing an image.

[Firmwares](FIRMWARES.md) &middot; [Downloads](ftp/README.md) &middot; [Online update](juis/README.md)
</div>
<div class="evo-card" markdown="1">
<strong class="evo-card__title">Explore Packages</strong>

Browse generated package, library, patch, theme, and host-tool listings.

[Packages](make/README.md) &middot; [Libraries](libs/README.md) &middot; [Patches](patches/README.md) &middot; [Themes](themes/README.md)
</div>
<div class="evo-card" markdown="1">
<strong class="evo-card__title">Try the Interface</strong>

Preview the EVO skin, mobile behavior, and browser-based administration experience without a device.

[Interactive mockup](screenshots/evo-demo.html) &middot; [Mobile/PWA notes](mobile.md) &middot; [Disk Management](make/disk-mgmt.md)
</div>
</div>
</section>

<section class="evo-section" markdown="1">
## EVO Focus Areas

<div class="evo-feature-grid" markdown="1">
<div markdown="1"><strong>Responsive web UI</strong><span>Modernized pages, mobile navigation, dark mode, PWA, and hardened session login.</span> [Read the EVO Skin overview](EVO-SKIN.md)</div>
<div markdown="1"><strong>Device operations</strong><span>Disk management, cloning, recovery, download tools, torrent workflows, and browser-based file administration.</span></div>
<div markdown="1"><strong>Runtime stacks</strong><span>Modern PHP, Python modules, QuickJS, Nginx, terminal tooling, and selected AI/ML packages.</span></div>
<div markdown="1"><strong>Disk Management subsystem</strong><span>Freetz-EVO integrates low-level Unix disk tools into a highly interactive graphical interface that orchestrates them into complete storage operations.</span> [Read the overview](DISK-MGMT.md)</div>
<div markdown="1"><strong>Audio subsystem</strong><span>USB DAC support, ALSA stack, MPD ecosystem, web radio, and AirPlay/Spotify receivers.</span> [Read the Audio Subsystem overview](AUDIO.md)</div>
<div markdown="1"><strong>Flasher tools</strong><span>USB peripheral integration: microcontroller flashers (avrdude, esp-serial-flasher, micronucleus, telink_tools), HID gateway and configurators (hidws, ja11-config), HID libraries and cdc-acm support.</span> [Read the Flasher Tools overview](FLASHER-TOOLS.md)</div>
<div markdown="1"><strong>Multimedia and downloads</strong><span>rTorrent/ruTorrent, aria2/AriaNg, Transmission frontends, elFinder file manager, and Gerbera UPnP/DLNA media server.</span> [Read the Multimedia overview](MULTIMEDIA.md)</div>
<div markdown="1"><strong>Rust packages</strong><span>Cross-compiled Rust tools for MIPS, x86, ARM, and Aarch64, with comprehensive uClibc compatibility patches.</span> [Read the Rust overview](RUST.md)</div>
<div markdown="1"><strong>Go packages</strong><span>Go 1.25 cross-compilation for all FRITZ!Box architectures, with per-package module cache isolation and CGO support.</span> [Read the Go overview](GO.md)</div>
<div markdown="1"><strong>Python ecosystem</strong><span>Python 3.14 with 70+ packages, Rust-built extensions, tkinter/X11, and Home Assistant support.</span> [Read the Python overview](PYTHON.md)</div>
<div markdown="1"><strong>Package reference</strong><span>Full listing of all new packages, enhanced packages, and CI/tooling additions.</span> [Browse all packages](NEW-PACKAGES.md)</div>
<div markdown="1"><strong>Build confidence</strong><span>Reviewed English documentation, stronger CI, upstream synchronization, and generated package listings.</span> [Check the testing workflow documentation](TESTING_WORKFLOW.md)
</div>
</div>
</section>

<section class="evo-section evo-reference" markdown="1">
## Documentation Map

<div class="evo-link-columns" markdown="1">
<div markdown="1">
<strong class="evo-column__title">Project</strong>

[Full README](REPO_README.md)<br>
[NEWS](NEWS.md)<br>
[CHANGELOG](CHANGELOG.md)<br>
[Support](SUPPORT.md)<br>
[Discussions](https://github.com/Ircama/freetz-evo/discussions)
</div>
<div markdown="1">
<strong class="evo-column__title">Generated Views</strong>

[Packages](make/README.md)<br>
[Libraries](libs/README.md)<br>
[Host-Tools](host-tools/README.md)<br>
[Source code](osp/README.md)<br>
[Stats](stats/README.md)
</div>
<div markdown="1">
<strong class="evo-column__title">Workflows</strong>

[Prerequisites](prerequisites/README.md)<br>
[Install](INSTALL.md)<br>
[Mobile access](mobile.md)<br>
[Sync upstream](SYNC_UPSTREAM.md)<br>
[Testing workflow](TESTING_WORKFLOW.md)
</div>
</div>
</section>

</div>

## Wiki

[//]: # ( WikiDYN )

[FAQ](wiki/00_FAQ/README.md)<br>
[Beginner](wiki/10_Beginner/README.md)<br>
[Advanced](wiki/20_Advanced/README.md)<br>
[Expert](wiki/30_Expert/README.md)<br>
[Troubleshooting](wiki/40_Troubleshooting/README.md)<br>
[Security](wiki/50_Security/README.md)<br>
[Development](wiki/60_Development/README.md)<br>
[Various](wiki/70_Various/README.md)<br>

[//]: # ( WikiEND )
