# SoX (Sound eXchange)
  - Homepage: [https://sourceforge.net/projects/sox/](https://sourceforge.net/projects/sox/)
  - Changelog: [https://sourceforge.net/p/sox/code/](https://sourceforge.net/p/sox/code/)
  - Package: [master/make/pkgs/sox/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/sox/)
  - Steward: -
  - Provides: `sox`, `play`, `rec` — Swiss Army knife of sound processing (`play` and `rec` are symlinks to `sox`)

SoX (Sound eXchange) is a command-line utility for converting, playing, and recording audio files. It supports a wide range of input/output formats and includes various audio effects.

Example of script (named `tones.sh`) to generate tone sequences, useful to test the audio output at various frequencies (20Hz - 20kHz).

```
#!/bin/ash

DEVICE="hw:0,0"
#DEVICE="default"
DURATION=3

for FREQ in $(seq 20 10 100) $(seq 200 100 900) $(seq 1000 1000 20000); do
    echo "${FREQ} Hz..."

    sox -q \
        -n \
        -r 48000 \
        -e signed-integer \
        -b 16 \
        -c 2 \
        -t alsa "$DEVICE" \
        synth "$DURATION" sine "$FREQ" 2>/dev/null
done
```
