# Addons
"Digitale Elite" addons are not supported here.

These addons appear to be implemented by people with little or no understanding of how Freetz works.<br>
As a result, failures are diverse and often severe. In some cases the Freetz configuration is damaged so badly<br>
that even after flashing a later image without addons, the FRITZ!Box may still not work correctly.

### Common problems reported in forums
This list is not guaranteed to be complete or perfectly accurate:
 - The Freetz web interface stops working entirely
 - `crond` no longer works
 - Online help pages no longer work
 - Freetz files are overwritten
 - A watchdog triggers reboots without reason, up to boot loops
 - Cron jobs repeatedly hammer external STUN/VoIP servers
 - Broken binaries are started and crash
 - Binaries packed with UPX also crash frequently
 - Invalid default config values cause segmentation faults
 - Some settings are saved twice
 - Other settings are no longer saved at all
 - Restoring configuration backups stops working
 - Users are deleted
 - Random system variable changes trigger segfaults in AVM binaries
 - Excessive and unnecessary flash writes accelerate wear
 - `rc.custom` is modified and not cleaned by flashing a clean image
 - ...

### Even worse combinations
This also explicitly applies to Sammy's `l-matic` script, because it not only installs these problematic DEB addons,<br>
it also performs additional invasive modifications inside Freetz.<br>

### How to recover
If you accidentally flashed an image with such addons, run a recovery and wipe all settings.
After that, flash Freetz again. **Do not restore an old backup.**<br>

### Issue policy
If something breaks and these addons were used, mention that clearly.
**Do not open issues here for images containing such addons.**


