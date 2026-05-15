# alsaequal 0.7.1
  - Homepage: [https://github.com/bassdr/alsaequal](https://github.com/bassdr/alsaequal)
  - Manpage: [https://github.com/bassdr/alsaequal#readme](https://github.com/bassdr/alsaequal#readme)
  - Changelog: [https://github.com/bassdr/alsaequal/releases](https://github.com/bassdr/alsaequal/releases)
  - Repository: [https://github.com/bassdr/alsaequal](https://github.com/bassdr/alsaequal)
  - Package: [master/make/pkgs/alsaequal/](https://github.com/Ircama/freetz-evo/tree/master/make/pkgs/alsaequal/)
  - Steward: Ircama

  - Depends on: `alsa-lib`
  - Provides: `/usr/lib/alsa-lib/libasound_module_pcm_equal.so`, `/usr/lib/alsa-lib/libasound_module_ctl_equal.so`
  - Configuration URL: `http://fritz.box:81/cgi-bin/conf/alsaequal` (with `alsaequal-cgi`)
  - Status URL: `http://fritz.box:81/cgi-bin/status/alsaequal` (with `alsaequal-cgi`)
  - Externalization: supported

`alsaequal` exposes a LADSPA-based equalizer through regular ALSA PCM and control devices, so applications can use system-wide equalization without knowing anything about LADSPA themselves.

The Freetz-EVO package ships the ALSA plugin modules only and leaves the actual LADSPA effect library as a runtime choice. A common pairing is CAPS `Eq10`, but any compatible LADSPA equalizer plugin can be used.

## Freetz integration

- optional `alsaequal-cgi` package for persistent equalizer settings, generated ALSA snippets, and runtime control from the web UI
- integrates with `alsa-utils` tools such as `amixer` for live control of the exported ALSA equalizer controls
- install footprint kept small by packaging just the ALSA bridge modules while using an external LADSPA plugin at runtime