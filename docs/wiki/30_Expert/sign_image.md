# Signing Firmware

Signing firmware means adding a
[digital signature](https://de.wikipedia.org/wiki/Digitale_Signatur) to
the firmware. This signature is currently used to verify whether the
firmware, or loadable parts of it such as AVM plugins, comes from a
trusted source and may therefore be flashed, loaded, and integrated. For
firmware images, AVM enforced this mechanism starting with Fritz!OS 6.5x.
Since then, the standard AVM web interface can flash only firmware from a
trusted source known to the firmware version running on the box at flash
time.

To understand what that last sentence means, it helps to review the basic
principles of digital signing. For deeper information, see any of the many
articles on the internet, for example this
[Wikipedia article](https://de.wikipedia.org/wiki/Digitale_Signatur).

Digital signing mainly involves these steps and facts:

-   A key pair is generated, consisting of a private key and a public key.
    The private key is protected by a password so it can only be used by a
    person who has both the key and its password.
-   The sender of a digital message uses the private key from the key pair
    to attach a digital signature to that message.
-   The digital signature lets the recipient verify authorship and
    integrity of the message with the public key, also called the
    verification key.

For this use case, that means:

-   The digital message is the firmware image.
-   The sender is the source from which the firmware image comes. The
    source must have the full key pair, both keys, and know the password
    protecting the private key.
-   The recipient is the firmware version running on the box at the time
    of flashing. It must have the public key, the verification key.

A digitally signed firmware image is classified as coming from a trusted
source if the public key for that source is known to the firmware running
on the box and the signature verification succeeds.

For understandable reasons, we do not have AVM's private secret key used
to sign original images. Even if we did, we would also need its password.
Therefore, the only option is to create a self-signed image and make the
firmware running on the box accept it. Two hurdles need to be overcome:

-   The mathematically and technically difficult part is understanding
    exactly what signing and signature verification mean inside AVM
    firmware. Fortunately,
    [PeterPawn](https://github.com/PeterPawn), a developer well known in
    the IPPF forum, did excellent work in his
    [YourFritz project](https://github.com/PeterPawn/YourFritz): he
    [documented](http://www.ip-phone-forum.de/showthread.php?t=286213)
    the mechanism and provided the corresponding
    [source code](https://github.com/PeterPawn/YourFritz/tree/master/signimage),
    which has since been integrated into Freetz.
-   As mentioned above, a signed image passes verification only if the
    firmware running on the box knows the source's public key. That is
    naturally not true for a self-signed image. Somehow, the public key
    must be smuggled onto the box. Once that has been achieved, every
    further self-signed image can be flashed through the regular AVM web
    interface, provided exactly the same key pair is used for signing and
    the public key is included in every new image.

Strictly speaking, the second task is not trivial. A separate article on
that topic was planned. Possible approaches include:

-   Downgrade, by recovery, to an older firmware version that still
    accepted unsigned images. From that older firmware version, flash a
    newer firmware version containing the custom public key.
-   If Telnet access to the box happens to be available, temporarily
    replace one of AVM's keys with your own using the bind-mount method,
    `mount -o bind ... ...`.
-   On NOR boxes, an image containing the public key can be transferred to
    the box with
    [push_firmware](http://trac_freetz_org/browser/trunk/tools/push_firmware).
-   On NAND boxes, an image containing the public key can be transferred
    with the
    [eva-to-memory method](https://github.com/PeterPawn/YourFritz/blob/master/eva_tools/eva_to_memory).

### Concrete Use in Freetz

-   Enable expert view in Freetz, `Level of User Competence` = Expert.
-   Under `Firmware packaging (fwmod) options`, enable `Sign image` and
    enter the password for the private key directly below it. The password
    is removed from the `.config` copy included in the image.
-   Build Freetz firmware normally.

Enabling these options has these effects:

-   If this is the very first run creating a self-signed image, the files
    needed for signing are generated and stored in the user's home
    directory with this prefix: `.freetz.image_signing`. The user must
    back up these files and use them from then on when building and
    signing all later images. In other words, it makes no sense to
    regenerate these files every time, because each new key would require
    solving the problem of how to get the newly generated public key onto
    the box again. This is also why the files are placed in the user's
    home directory rather than in the Freetz build directory itself. If
    several build directories are used for different boxes, each box still
    uses the same key pair. These files must be backed up by the user and,
    for example after changing build systems, copied manually to the new
    system.
-   If the files already exist, they are simply used. The public key is
    included in the image in a special format under the name
    `/etc/avm_firmware_public_key9`; see PeterPawn's detailed description
    for the format.
-   Once your public key is on the box, every further image signed with
    exactly the same key pair can be flashed through the AVM web interface.


