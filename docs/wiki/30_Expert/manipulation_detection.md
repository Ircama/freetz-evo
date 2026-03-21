# How FRITZ!Box Detects Unsupported Changes

The FRITZ!Box overview page may show a warning similar to:

> Unsupported changes were detected on your FRITZ!Box.

This page explains where that warning comes from and how to diagnose it.

## Typical Causes

The warning is commonly triggered by one or more of these events:

- Telnet login activity.
- Firmware updates that are not vendor-signed (including modified images).
- Imported configuration states marked as non-standard.

## Where the State Is Stored

The device stores internal flags in persistent flash areas that are not exposed like regular editable files in /var/flash.

## Reading the Flags

On a shell (SSH/Telnet), eventsdump can reveal the marker line:

```sh
eventsdump -d | head -n 1
```

Possible outputs include values such as:

- DEBUGCFG
- TELNET
- NOT_SIGNED
- IMPORT
- Combinations of the above

If no marker is present, the first line may be the regular event log output.

## Technical Background

The eventsdump tool reads internal attributes through a character device node that maps to firmware attribute storage. With tracing tools you can observe this access pattern:

- Create node
- Open/read content
- Print flags
- Remove node again

Exact major numbers can vary by device/firmware generation. The mechanism is implementation-specific and can change across releases.

## Operational Guidance

- Treat this warning as expected after modding-related actions.
- Prefer SSH over Telnet for normal maintenance.
- Keep a known-good recovery image ready before experiments.
- Document your own changes so warnings are easy to correlate.

## About Clearing the Warning

Historically, users discussed techniques to clear or hide this state. Those methods are fragile, firmware-dependent, and can introduce side effects. For reliable operation, prefer a clean supported state (recover/reflash) instead of trying to suppress detection flags.

## Recovery-Focused Approach

If you want a clean baseline:

1. Back up required user data.
2. Recover to stock firmware.
3. Verify normal behavior.
4. Reapply only the minimum required customizations.

This keeps troubleshooting predictable and reduces risk during future updates.
