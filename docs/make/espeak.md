# eSpeak 1.48.04 (binary only) - DEPRECATED
  - Package: [master/make/pkgs/espeak/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/espeak/)
  - Steward: -

eSpeak is a "text to speech" generator, or in other words a "reading
aloud" program that can play back ("read aloud") ASCII text with a
synthetic voice. In Freetz it is used, among other things, by
[DTMFBox](dtmfbox.md).

### Installation

To install it, simply select the package in the package menu of
`make menuconfig`. Support for numerous additional languages can be
selected again (as a "bundle") once the package itself has been selected.
This makes sense at the latest when multiple languages are needed.

Anyone who needs speech output only for DTMFBox does not necessarily have
to install the eSpeak package: DTMFBox also supports so-called
"WebStreaming" (the audio data is then generated on another server),
which, however, requires an existing internet connection.

### Invocation

Only a few **short** tips for invoking eSpeak are given here; details can
be found on the [project page](http://espeak.sourceforge.net/commands.html):

`espeak "Hello world"` simply says "Hello world" with the default
settings. This can sound rather strange if, for example, English is set
as the default language. Therefore, both language and speaker can be
passed as parameters: `espeak -vde+f3 "Hallo Welt"` lets the same text be
whispered by a German female voice. Correctly guessed: "-vde" selects
German ("-ven" English), "+f" stands for "female" (of which there are at
least the different "models" +f1, +f2, +f3), and there are also
(+m1, +m2, +m3) "male" voices. The "+XX" part can also be omitted if
only the language should be specified.

If the voice rushes too much, the `-s` parameter can be used to adjust
the "speed" (`-s 170` is a good starting value). The pitch can also be
influenced: `-p 50` sets the "pitch" to 50 (a good starting value).
Higher values make male voices sound like eunuchs; lower values turn
"present ladies" into "bearded ladies".

### Note

The executable can be found on the box under `/usr/bin/speak`.

### Further Links

-   [http://espeak.sourceforge.net](http://espeak.sourceforge.net)

