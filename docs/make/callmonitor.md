# Callmonitor 1.20.9-git
  - Package: [master/make/pkgs/callmonitor/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/callmonitor/)
  - Steward: -

The Callmonitor makes it possible to execute arbitrary actions on a
FritzBox for incoming calls, depending on who calls whom. Popular uses
include sending notifications to various kinds of "boxes" (TV/satellite
receivers, game consoles, PCs) or waking devices (Wake on LAN).

With a reverse lookup in internet telephone directories, the caller's name
can often also be displayed.

The special thing about this Callmonitor, unfortunately there are many
projects with similar names, is that it runs entirely on the FritzBox. It
is therefore not necessary to keep additional computers switched on.

## Installation

[![[Callmonitor WebInterface]](../../docs/screenshots/6_md.png)](../../docs/screenshots/6.png)

The Callmonitor is implemented as a package within Freetz
([forum](http://www.ip-phone-forum.de/showthread.php?t=85371)) and can
simply be selected during its installation.

The Callmonitor package cannot be installed as an addon package.

## Installing New Versions

Please note: with Freetz 1.1, only Callmonitor versions up to 1.15 can be
used. Callmonitor 1.15.1 and higher require changes that are included in
Freetz 1.2 or the Freetz development version.

To include the latest version from the development version in Freetz 1.2,
you can proceed as follows in the root directory of Freetz:

```
svn switch http://svn_freetz_org/trunk/make/callmonitor/callmonitor.mk make/callmonitor/callmonitor.mk
```

## Further Links

-   [Development page at SourceForge](http://sourceforge.net/projects/callmonitor/)
-   [Forum page for questions and discussions](http://www.ip-phone-forum.de/showthread.php?t=191723)

## Configuration

The Callmonitor configuration is best performed in several steps, spread
across different pages in the Freetz web interface:

1.  Perform basic configuration, described below.
2.  Define listeners for specific actions.
3.  Test the configuration with a test call.

## Basic Configuration

Some fundamental settings can be configured on the Packages-Callmonitor
page of the web interface.

First, choose the start type, normally "Automatic", because otherwise the
Callmonitor has to be started manually after every FritzBox restart. If
there are problems, debug output can additionally be enabled, but this is
normally unnecessary.

The next block only provides links to the listeners and to running test
calls.

In the following block, the location information (country and area code)
can be checked again and also adjusted through a link to the AVM WebGUI.
Note that changes to the country and/or area code are shown on the
Callmonitor page only after the Callmonitor has been restarted.

But we are not there yet; first, the reverse lookup settings in the third
block still have to be checked. Reverse lookup can be disabled completely;
the checkbox before "Perform reverse lookup for" is responsible for this.
If it should be used, the "Service for reverse lookup" can be selected,
to which the requests are sent. **Attention:** this function requires an
existing internet connection, so some kind of always-on flat rate for
internet access is recommended, for example a volume tariff or complete
flat rate.

If the telephone number cannot be found, for example because the
subscriber has objected to reverse lookup, the area code is looked up at
the selected service instead. This at least allows the location to be
displayed. Finally, it can be selected whether the reverse lookup results
are stored permanently in the phone book (that is, in the box flash) or
temporarily in memory until restart. It is also possible to disable
caching entirely. Then reverse lookup is performed again and again, even
if the same phone number has already been looked up once.

The setting "Area code for local phone numbers" is needed because in the
local network the area code is not always transmitted. In current
versions, the area code is automatically taken from the internet telephony
settings in the AVM web interface.

## Defining Listeners

Next, so-called listeners must be defined. On incoming calls they start
the desired action. More details are available on a special page for the
listeners.

## Test Call

Once the listeners have been defined, they can and should be tried with a
test call. Of course, a real call can be made, but often there is no way
to test special rules. Therefore, there is the option to generate a test
call through the web interface.

## Troubleshooting

The output of the test call and, if applicable, debug messages usually
provide enough hints as to why the action was not executed or why the
Callmonitor does not start. To see the log, first enable this option in
the Freetz configuration so it is built into the image. It is also worth
looking at the maintenance page: if the Callmonitor interface is disabled,
the Callmonitor cannot work either. Enabling it with a call to the
FritzBox from an attached telephone using the number #96*5* can help. If
none of this helps, support is available on the [forum page for questions
and discussions](http://www.ip-phone-forum.de/showthread.php?t=100706).

## Rules (Listeners)

The listeners file contains a list of rules that determine which actions
should be executed under which conditions.

Blank lines are ignored, as are lines beginning with *#*; those are
comments.

Each rule is on one line and consists of four values, separated by
whitespace, in this order:

1.  Event
2.  Source phone number: pattern for SOURCE
3.  Destination phone number: pattern for DEST
4.  Action: arbitrary shell code

The two patterns for *SOURCE* and *DEST* are [extended regular
expressions (ERE)](http://www.selflinux.org/selflinux/html/regex.html),
as understood by *egrep*. The event (incoming/outgoing call; ringing,
acceptance, etc.) is specified with the syntax shown below.

Negative patterns can be used in listeners by prefixing an exclamation
mark: `!123` matches all numbers that do not contain 123 anywhere.

Examples:

```
  Pattern          matches
  ---------------- ---------------------------------------------------------------------
  `^`              all numbers
  `^034`           numbers beginning with 034
  `4563$`          numbers ending with 4563
  `!^(045|0164)`   numbers that **do not** begin with 045 or 0164
  `^0123456$`      only exactly the number 0123456
  `^04553...$`     numbers where exactly three more characters follow 04553
  ---------------- ---------------------------------------------------------------------
```

All rules are processed in parallel; a specific order is not guaranteed.

For the listeners to be editable through the Freetz web interface, its
security level must be set to 0. This is necessary because arbitrary code
can be executed through the listeners.

[![[Callmonitor: Listener configuration]](../../docs/screenshots/20_md.png)](../../docs/screenshots/20.png)

## Format

Since version 1.0 of the Callmonitor, the following format applies to the
listeners, allowing different reactions to up to eight different events:

-   ***:request**: call arrives (it rings)
-   ***:cancel**: call was canceled before a connection was established,
    allowing direct reaction to "missed calls"
-   ***:connect**: connection begins
-   ***:disconnect**: connection was ended

In addition, there is a distinction between

-   **in:***: incoming and
-   **out:***: outgoing calls.

This yields the following set of events:

```
  |           *:request       *:cancel       *:connect       *:disconnect
  ----------- --------------- -------------- --------------- ------------------
  | in:*      in:request      in:cancel      in:connect      in:disconnect
  | out:*     out:request     out:cancel     out:connect     out:disconnect
  ----------- --------------- -------------- --------------- ------------------
```

Accordingly, the listeners received an additional first column in which
the desired event for the rule can be specified, using abbreviations and
wildcards:

```
in:request  ^       ^1234$  xboxmessage xbox
in:cancel   ^       ^       mailmessage -t test@example.com
out:cancel  ^1234$  ^0123   dboxpopup dbox-a "${DEST} does not pick up"
*:dis       ^       ^       echo "Call ended: ${DURATION} seconds" >> log
```

There can be multiple rules that match the same event.

The prefixes "NT:", "E:", and "*:" in the *SOURCE* column no longer
exist. Your previous listeners file from before version 1.0 cannot simply
be reused. However, on first startup the CallMonitor tries to perform a
rough conversion to make the transition easier. In any case, the
listeners should be checked once after the conversion.

Columns 2 and 3 in the listeners are still patterns (regular expressions)
for source and destination phone number (*SOURCE* and *DEST*). However,
note that columns 2 and 3 must contain the MSNs, meaning the internet
phone numbers, and no longer values such as *SIP0* or *SIP1* as before.

## Event Information for Actions

Actions receive information about the triggering call in environment
variables. In shell scripts, they are referenced with a $, for example
`echo $SOURCE_NAME`.

```
  Variable          Content                                                                                                                                    | since version
  ----------------- ------------------------------------------------------------------------------------------------------------------------------------------- -----------------
  EVENT             the triggering event                                                                                                                        1.0
  ID                the call ID, directly from the Callmonitor interface                                                                                         1.0
  UUID              globally unique ID for this call, not just this event                                                                                        1.20
  TIMESTAMP         time of the event, in "DD.MM.YY HH:MM" format                                                                                               1.0
  SOURCE            source phone number                                                                                                                         ---
  SOURCE_DISP       more display-friendly variant of SOURCE, with country code removed, call-by-call prefixes removed, etc.                                      1.8
  SOURCE_NAME       source name, if it could be determined                                                                                                       ---
  SOURCE_ADDRESS    the address (street, city, country) is available separately since 1.12 and is no longer included in SOURCE_NAME                              1.12
  SOURCE_ENTRY      the complete phone book entry, corresponding to SOURCE_NAME before 1.12                                                                      1.12
  DEST              destination phone number                                                                                                                     ---
  DEST_DISP         more display-friendly variant of DEST, with country code removed, call-by-call prefixes removed, etc.                                        1.8
  DEST_NAME         destination name, if it could be determined                                                                                                  ---
  DEST_ADDRESS      the address (street, city, country) is available separately since 1.12 and is no longer included in DEST_NAME                                1.12
  DEST_ENTRY        the complete phone book entry, corresponding to DEST_NAME before 1.12                                                                        1.12
  EXT               extension, if known, directly from the Callmonitor interface                                                                                  1.0
  DURATION          for *:disconnect, the call duration in seconds                                                                                               1.0
  PROVIDER          service provider through which the call is handled ("POTS" for landline or "SIP0", "SIP1", ... for the different SIP providers)            1.5
  ----------------- ------------------------------------------------------------------------------------------------------------------------------------------- -----------------
```

On a FritzBox 7050, EXT can have the following numerical values. For an
incoming call, this information is only available from in:connect onward;
before that the assignment is not yet clear.

```
  Value    Meaning
  -------- ------------------
  0        FON 1
  1        FON 2
  2        FON 3
  3        direct dial-in
  4        Fon S0
  5        Fon/Fax PC
  6        answering machine
  36       Data S0
  37       Data PC
  -------- ------------------
```

## Formatting Output

The following functions are available for formatting output:

Since version 1.8:

-   f_duration: displays time durations as "hh:mm:ss"

    ```
    f_duration <TIME_IN_SECONDS>

      TIME_IN_SECONDS:      time in seconds, e.g. $DURATION
    ```

Example:

```
    echo "The call lasted $(f_duration $DURATION)"
```

produces the output

```
The call lasted 1:05:03
```

if DURATION has the value 3903.

The constant $LF can also be useful; it contains a line break (line
feed):

```
    dboxmessage foo.bar "Line 1${LF}Line 2"
```

## Patterns for Events

There are several ways to specify in the listeners which events should
trigger a rule:

-   Complete event names:

    ```
    in:request
    out:disconnect
    ```

-   Abbreviations of the front and/or rear part:

    ```
    in:req
    out:disc
    i:r
    o:d
    ```

-   Wildcards for the front part (direction), the rear part, or both:

    ```
    *:req
    ou:*
    *
    ```

-   Lists of these components, separated by commas. Caution: no
    whitespace. The rule matches if one of the parts matches:

    ```
    in:req,out:*
    ```

## Examples:

Send a missed call (in:cancel) mailmessage to several email addresses:

```
in:cancel ^ ^ mailmessage -t user1@example.com,user2@example.com
```

Call a fixed phone number (0401234568) from a specific phone number
(0401234567) and switch on the PC via WOL (Wake on LAN):

```
in:request ^0401234567 ^0401234568 ether-wake -i eth0 00:13:DE:01:A4:DE
```

Display notifications on a TV via Dreambox with Enigma2:

```
in:request ^ ^ dream2message --user=root --pass=dreambox 192.168.178.104
```

Email notification on fax receipt:

```
in:disconnect ^ 0401234567$ mailmessage -s "Fax received from $SOURCE"
```

## Events

A successful incoming call generates the following events in sequence;
analogous for outgoing calls with `out:*`:

1.  in:request
2.  in:connect
3.  in:disconnect

A call that is canceled before the other party accepts it generates the
following events:

1.  in:request
2.  in:cancel

The events are not directly the raw events visible on the JFritz
interface (port 1012), but are created from them, with the same ID, using
a finite automaton. In the diagram, input events are shown above the
edges and output events below; the event `in:accept` is used only
internally.

[![[CallMonitor: events]](../../docs/screenshots/36_md.png)](../../docs/screenshots/36.png)

## Actions

Actions are executed based on rules defined in the so-called listeners.
Any shell code (programs/commands) known to the FritzBox can be executed.
The actions must be passed in the listener as the <action> parameter; see
the example image below for the *dboxpopup* action. Environment variables
with information about the triggering call can be used.

Some standard functions are provided directly by the Callmonitor and are
described below. With the script *callaction*, all Callmonitor actions can
be called from outside, for example from the command line for testing.

If newly arrived emails from *checkmaild* should be displayed on a VDR,
this can be done by creating the file `/var/mod/etc/maillog.cfg`, for
example as follows:

```
    #!/bin/sh
    # new email received
    if [ "$1" = "0" ];
    then
       callaction vdr m741 "On $6 at $7, $8 wrote: $9"
    fi
```

Background information about the file `maillog.cfg` and the checkmaild
package can also be read here in the wiki under
[checkmaild](../checkmaild/README.mk).

## Notify

Notifications are used to signal incoming and/or missed calls through
various communication paths and on various devices.

The predefined default texts of the functions can be adapted to your own
needs.

Functions based on getmsg:

-   DGStation Relook 400S
-   DBox
-   DreamBox
-   XBox
-   Freecom MusicPal

If necessary, passwords and user names can also be specified when
calling.

Functions based on rawmsg:

-   SoundBridge by Roku
-   VDR
-   YACwiki}: Yet Another Caller ID Program

Notification by entirely different means:

-   mailmessage: notification by mail
-   Samsung TV: notification SOAP message
-   Snarl: notification for Snarl

## Dial, Wake, Configure

-   Dialing assistance: addressing the FritzBox dialing assistance
-   WOL}: Wake on LAN
-   Fritz!Box configuration: switch WLAN, SIP, and port forwarding on and
    off

## Custom Actions

With the two basic functions *getmsg* and *rawmsg*, almost arbitrary
functions can be executed on the target machines, provided they are
implemented there accordingly, either started via the web server or
listening on a TCP port.

-   getmsg: HTTP GET requests
-   rawmsg: messages over "raw" TCP connections
-   Calling: notes about function calls

Other self-defined actions are also possible:

-   Self-defined actions

## Third-Party Software

CallMon2: Perl script running on Windows and Linux,
[http://zephyrsoftware.sf.net/](http://zephyrsoftware.sourceforge.net/?q=fritzbox/callmon2)
(there you will find exact information about setting the whole thing up!)

## Phone Book (Callers)

Format:

```
<Phone number with area code>` `<Name>(`;` <Address>)
```

Reverse lookup results can be stored here for faster access in the
future. Of course, number-name pairs can also be entered or changed
manually.

-   49-style phone numbers without 00 and longer than 10 characters are
    recognized.
-   The name of the called party is available, especially for SIP0 through
    SIP9. The assignment to names can be made in the phone book (Callers),
    either directly for SIP0 through SIP9 or for addresses of the form
    "username@registrar". The latter has the advantage that nothing in
    the phone book has to be adjusted if the SIP accounts are entered in
    a different order. During startup, short names are generated for all
    accounts and entered as defaults in the Callers.
-   Search strategy: first look up the number unchanged in the local phone
    books (Callers, AVM phone book), then normalize it, possibly adding
    area/country code; SIP[0-9] becomes username@registrar, and try
    locally again. Only then try reverse lookup on the internet.

[![[Callmonitor Callers]](../../docs/screenshots/216_md.png)](../../docs/screenshots/216.png)

## HTTP Requests (getmsg)

The function `getmsg` sends a notification by sending it to a web server
via HTTP GET. It is possible to specify the URL (only path plus query
string, meaning the part after the host name) with [printf
templates](http://www.gnu.org/software/libc/manual/html_node/Formatted-Output.html).
In the simplest case, this means that the position in the URL where the
message should be inserted is marked with `%s`. `getmsg` itself ensures
correct encoding of messages (URL encoding).

## Syntax:

```
  Usage:  getmsg [OPTION]... <HOST> <url-template> [<message>]...
          getmsg [OPTION]... -t <url-template> <host> [<message>]...
  Send a message in a simple HTTP GET request.

    -t, --template=FORMAT  use this printf-style template to build the URL,
                           all following messages are URL-encoded and filled
                           into this template
    -d, --default=CODE     default for first parameter (eval'ed later)
    -p, --port=PORT        use a special target port (default 80)
    -w, --timeout=SECONDS  set connect timeout (default 3)
    -v, --virtual=VIRT     use a different virtual host (default HOST)
    -U, --user=USER        user for basic authorization
    -P, --password=PASS    password for basic authorization
        --help             show this help
```

The **following functions are based** on `getmsg` and therefore support
the same options. The URL template (`-t`), the default message (`-d`), and
the port (`-p`) are already preset appropriately for the respective
receiver.

## Example:

```
*:* ^ ^ getmsg 192.168.0.111 -p 222 -t "/home/phone?event=%s&id=%s&time=%s&source=%s&source_name=%s&destination=%s&destination_name=%s&extension=%s&duration=%s&provider=%s" "${EVENT}" "${ID}" "${TIMESTAMP}" "${SOURCE}" "${SOURCE_NAME}" "${DEST}" "${DEST_NAME}" "${EXT}" "${DURATION}" "${PROVIDER}"
```

The example above causes a GET call to
[http://192.168.0.111:222/home/phone](http://192.168.0.111:222/home/phone)
with all relevant data in the query string.

## DBox2

## DBox2 with Neutrino Image

```
  dboxmessage (default_dboxmessage)
  dboxpopup (default_dboxpopup)
```

The functions differ only in whether the displayed message disappears by
itself after some time or must be explicitly confirmed.

default_dboxmessage and default_dboxpopup have the function default_dbox
as their common basis.

```
  dboxlcd (default_dboxlcd)
```

Displays a message on the DBox LCD.

## DBox2 with Enigma Image

If you have an Enigma image on your box and "popup=" or "nmsg=" appears
in the popup before the actual text, you can use the following command as
with the Dreambox:

```
  dreammessage (default_dreammessage)
```

## Dialing Assistance

The dialing assistance known from the AVM web interface is available here
as a function since Callmonitor 1.1.

```
dial NUMBER [PORT]
```

The first argument is the number to dial, the second optional argument is
the port (1, 2, 3, 50, 51, ...), of course without square brackets.

Ports 1 through 3 are the analog telephones, 50 is all ISDN telephones,
and from 51 onward the individual ISDN telephones.

Hanging up is also possible since Callmonitor 1.5:

```
hangup [PORT]
```

## Self-Defined Actions

Custom actions can be stored as shell functions in one or more files
`/tmp/flash/callmonitor/actions.local.d/*.sh`. Standard functions can
also be overwritten this way, for example `default_message()`.

Of course, arbitrary external programs can also be called.

## User Names and Passwords

All actions based on `getmsg` understand the following options, with
which user name and password for the target box web interface can be
specified:

```
  -U USERNAME
  --user USERNAME
  -P PASSWORD
  --password PASSWORD
```

The data can also be specified directly in the host name in short form:

```
  USERNAME:PASSWORD@HOST:PORT
```

## Example

For example:

```
  dboxmessage john:secret@mydbox
```

This has the same effect as

```
  dboxmessage --user=john --password=secret mydbox
```

or

```
  dboxmessage -U john -P secret mydbox
```

Or if the D-Box listens on a port other than the default port:

```
  dboxmessage john:secret@mydbox:3818
  dboxmessage --user=john --password=secret --port=3818 mydbox
```

## Freecom MusicPal

Version 1.15.1 contains the new action **musicalpalmessage**, which can
display messages on the display of a Freecom MusicPal. A maximum of two
lines is supported; the display duration, 25 seconds by default, can be
changed through the environment variable MUSICPAL_TIMEOUT. If the display
should be released earlier, the action **musicalpalclear** is available.

Some examples:

```
    # default message, user name and password "admin"
    musicpalmessage musicpal.domain.my

    # custom message with two lines, different credentials
    musicpalmessage --user="root" --password="secret" musicpal.domain.my "Important call${LF}from ${SOURCE}!"

    # alternative syntax
    musicpalmessage root:secret@musicpal.domain.my "Important call${LF}from ${SOURCE}"

    # clear message
    musicpalclear musicpal.domain.my
```

To customize the default message, the shell function
`default_musicpalmessage` can be overwritten.

## Roku SoundBridge

The [Roku SoundBridge](http://www.rokulabs.com/products_soundbridge.php)
can display messages on its display. Since Callmonitor 1.12.4, three
functions are available for controlling it:

```
  sbmessage
  (default_sbmessage)
```

For displaying a static message. The display duration can be determined
with the environment variable `SB_TIMEOUT`.

```
  sbmarquee
  (default_sbmarquee)
```

For displaying scrolling text. The environment variable `SB_TIMES`
specifies how many times the message should be repeated.

```
  sbxmessage
  (default_sbxmessage)
```

For displaying a static, multi-line message. The display duration can be
determined with the environment variable SB_TIMEOUT.

## VDR

VDR: Video Disk Recorder,
[http://www.cadsoft.de/vdr/](http://www.cadsoft.de/vdr/)

```
  vdr [OPTION]... [MESSAGE]
  (default_vdr)
```

## Notification on a Samsung TV

The function `samsung` sends a notification about a phone call to a
Samsung TV using the SOAP method:

```
samsung {IP of the TV}
```

For example:

```
samsung 192.168.178.19
```

The caller name, if entered in the phone book or Callers, otherwise the
phone number, the called number, and date and time are displayed. The
length of displayable characters depends on the content. If no more text
can be displayed, for example with address additions in the Callers, it
is cut off at the end so it ends with "...".

The listener entry in the Callmonitor can look like this, for example:

```
in:request ^ ^ samsung tv
```

For testing, the following can be executed directly from the FritzBox
terminal:

```
callaction samsung tv
```

The function `samsung_text` sends a message to a Samsung TV using the
SOAP method, for example:

```
echo "Hello, world!" | callaction samsung_text 192.168.178.19 \
--from="Sender" --from-number="069 123456" \
--to-number="089 987654" --to="Recipient" \
--date="2010-05-21" --time="21:56:00"
```

Analogous to the example above, caller name and phone number, recipient
name and phone number, as well as date and time are displayed. That means
the message is sent using the same method (SOAP) as the notification
about a phone call, plus the data mentioned above.

## Snarl

[Snarl](http://www.fullphat.net/index.php) is similar to Growl, which
some may know. It is a notification program that runs in the background
and can be addressed by various programs, etc. The advantage is that this
provides user-defined, system-wide uniform notifications.

Snarl uses its own protocol called SNP ([Snarl Network
Protocol](http://www.fullphat.net/dev/snp/index.htm)).

Using "rawmsg", a message is sent to an IP (port 9887) in the network,
on which Snarl itself must be listening. Snarl then displays this
notification transmitted by the Callmonitor via SNP.

For example like this:

```
echo -n "type=SNP#?version=1.0#?action=notification#?title=Call#?text=${SOURCE}#?timeout=20"$'\r\n' | nc IP 9887
```

(buehmann showed how it works in this
[thread](http://www.ip-phone-forum.de/showthread.php?t=216938). Thanks!)

## Listener Entry:

The listener entry in the Callmonitor can look like this, for example:

```
in:request ^ ^ echo -n "type=SNP#?version=1.0#?action=notification#?title=incoming call#?text=from ${SOURCE} - ($SOURCE_NAME)${LF}for ${DEST_NAME} - (${DEST_DISP})${LF}#?timeout=20#?icon=C:\pic.png"$'\r\n' | nc 192.168.178.20 9887
```

## Screenshots:

A notification from Snarl could then look like this. The information
about caller, phone number, event, etc. can of course be adjusted or
extended accordingly using the Callmonitor.

> [![[Snarl example]](../../docs/screenshots/171_md.png)](../../docs/screenshots/171.png)
>
> [![[Snarl example]](../../docs/screenshots/167_md.png)](../../docs/screenshots/167.png)
>
> [![[Snarl example]](../../docs/screenshots/173_md.png)](../../docs/screenshots/173.png)

> Important: "Curl" or "getmsg" cannot be used; they are suitable only
> for the HTTP protocol and do not work with Snarl's SNP.

## XBox

For this function, [XBox Media Center
(XBMC)](http://www.xboxmediacenter.com) must be running, and the web
server must be enabled there under *Settings -> Network*. If necessary,
pass port, username, and password with the options (see above). XBMC then
displays the message in a small window that closes automatically.

```
  xboxmessage (default_xboxmessage)
```

The XBox does not allow commas in messages with `xboxmessage`. The title
of the message can be influenced through the environment variable
`XBOX_CAPTION="Phone call"`.

## Adjustments on the XBox

Display duration and window size can be adjusted in the file
`DialogKaiToast.xml`. Depending on the selected TV type, the respective
file under `skin\Project Mayhem III\PAL\` or
`skin\Project Mayhem III\PAL16x9\` is responsible. The following
revision of the "PAL" file achieves a usable result (only changed lines):

```
...
  <coordinates>
    <system>1</system>
    <posx>275</posx>
    <posy>420</posy>
  </coordinates>
  <animation effect="slide" time="5000" start="300,0">WindowOpen</animation>
  <animation effect="slide" time="5000" end="300,0">WindowClose</animation>
...
    <control>
      <description>Popup Kai Toast Dialog Background</description>
      ...
      <width>400</width>
      <height>125</height>
...
    <control>
      <description>avatar</description>
      ...
      <posx>40</posx>
      <posy>25</posy>
...
    <control>
      <description>Caption Label</description>
      ...
      <posx>46</posx>
      <posy>30</posy>
      <width>305</width>
...
    <control>
      <description>Description Button</description>
      ...
      <posx>46</posx>
      <posy>46</posy>
      <width>305</width>
...
```

## Further Possibilities

There is also a [Python
script](http://ca.geocities.com/farside@rogers.com/Scripts/callerid.html)
that enables CallerID display on the Xbox. The message can then be sent
to the XBox with the function `yac`. The script is also included in
[xbmcfritz](http://www.xbmc.de/xbmc/download.php?view.150), which can
also display the FritzBox call list on the XBox.

## YAC

YAC: Yet Another Caller ID Program,
[http://sunflowerhead.com/software/yac/](http://sunflowerhead.com/software/yac/)

Syntax:

```
  yac <IP>
    IP       IP of the computer on which the YAC listener runs
```

## General Notes on Function Calls

Calling functions based on getmsg or rawmsg always looks like this:

```
  foomessage [OPTION]... <host> [<message>]...
```

The simplest and most commonly used case is therefore

```
  foomessage <host>
```

All options understood by getmsg or rawmsg can be used as options.

The default message is generally generated by a function following the
name convention `default_foomessage` and can therefore be overwritten
easily.

Environment variables can sometimes be used with the functions. They are
set before the function call. The Callmonitor automatically takes care of
encoding environment variables that contain text, for example
`XBOX_CAPTION` and `DREAM_CAPTION`. So you can simply write

```
  FOO_CAPTION="This is the 100% correct title" foomessage <host>
```

without having to worry about encodings (URL or printf).

## FritzBox Configuration

The `config` action from `config.sh` (since Callmonitor 1.8) can be used
to change some FritzBox configuration functions.

## Port Forwarding

Port forwarding can be enabled and disabled.

```
Syntax:
  config forward <NUMBER> <on|off|toggle>

    NUMBER                 number of the port forwarding rule, beginning at 1
    on|off|toggle          switch port forwarding on or off, or toggle it
                           depending on the existing setting
```

Examples:

```
    config forward 1 on     # enable 1st port forwarding rule
    config forward 3 off    # disable 3rd port forwarding rule
    config forward 5 toggle # toggle 5th port forwarding rule
```

## WLAN

WLAN can be enabled and disabled.

```
Syntax:
  config wlan [2.4|5|guest] <on|off>

    2.4|5                  desired frequency band: 2.4 or 5 GHz
    guest                  switch guest WLAN (since version 1.20.1)
    on|off                 switch WLAN on or off
```

If the frequency band is omitted, both are switched, but only the 2.4 GHz
band is queried.

Examples:

```
    config wlan off      # WLAN off
    config wlan on       # WLAN on
    config wlan 2.4 off  # WLAN in 2.4 GHz band off
    config wlan 5 on     # 5 GHz WLAN on
```

## DECT

DECT can be enabled and disabled.

```
Syntax:
  config dect <on|off>

    on|off                 switch DECT hardware on or off
```

Examples:

```
    config dect off      # DECT off
    config dect on       # DECT on
```

## SIP

SIP accounts can be enabled and disabled.

```
Syntax:
  config sip <NUMBER> <on|off>

    NUMBER                 number of the SIP account, beginning at 1
    on|off                 switch SIP account on or off
```

Examples:

```
    config sip 4 on      # enable 4th SIP account
    config sip 2 off     # disable 2nd SIP account
```

## Call Diversion

(De)activation of call diversions (since version 1.8.2). Currently only
call diversions of the type "Calls from phone number xy" are supported,
not "All calls to Fon X".

```
Syntax
  config diversion <NUMBER> <on|off>

    NUMBER                 number of the call diversion, beginning at 1
    on|off                 switch call diversion on or off
```

## Querying Configuration Values

Since version 1.9.1.

Simply omit the value in the config call:

```
    config sip 2
    config diversion 1
    config forward 3
    config wlan
```

Output is one of the values "on", "off", or "error", for example if the
dialing rule does not exist.

## Alternative

In newer firmware versions, the Callmonitor is not necessarily required
to display or change these functions. Alternatively, they can be edited
with AVM's [ctlmgr_ctl](http://wehavemorefun.de/fritzbox/index.php/Ctlmgr_ctl).

## DreamBox

## Dreambox with Enigma 1

```
  dreammessage [user[:password]@]host[:port] ["Alternative message"]
```

[![[CallMonitor: disable Dreambox auth]](../../docs/screenshots/1_md.jpg)](../../docs/screenshots/1.jpg)

As can be seen, "host" (that is, computer name or IP address) is the only
required parameter. For the message to actually arrive, authentication
must be taken into account. One solution, as shown in the attached
screenshot, is disabling message authentication on the box itself. Anyone
who does not want this currently has only the option of prefixing the host
with `user:password@`, which is then shown in plain text in the
listeners.

`dreammessage` has a standard message template that is normally used.
Anyone who would rather format the message themselves can find a list of
usable placeholders for phone number, line breaks, and so on in the
listeners.

Furthermore, there are three environment variables that influence the
behavior of `dreammessage`. They are shown here in a typical call with
their default values:

```
  DREAM_TIMEOUT=10 DREAM_CAPTION="Phone call" DREAM_ICON=1 dreammessage box1
```

## Standby Check

If the Dreambox to be notified is in standby, messages are buffered until
it wakes up again. This is nice in itself, but if it has not been used
for a few days and then, after switching it on, hundreds of "missed"
calls are shown, it becomes less pleasant. It would therefore be
practical for some if messages were delivered only when, at the time of
the call, the Dreambox is *not* in standby, and otherwise notification
were completely suppressed.

Fortunately, this is feasible; tested with DM600, DM7000, and DM7020. The
status can be determined as follows:

```
    # no password authentication active:
    standby=`wget -O- "http://dreambox/cgi-bin/status" | awk '/Standby/' | sed -e 's/<[^>]*>//g'`
    # with password authentication:
    standby=`wget -O- --http-user=root --http-passwd=dreambox "http://dreambox/cgi-bin/status" | awk '/Standby/' | sed -e 's/<[^>]*>//g'`
```

Depending on whether the WebIF is configured for password authentication
or not, the corresponding variant can be used. However, busybox-wget does
not support authentication. Therefore the package 'wget' must be
installed when building Freetz. The variable `$standby` is subsequently
set either to `STANDBY:ON` or `STANDBY:OFF`. For our notification action,
we can use it as follows:

```
    [ "$(wget -O- "http://dreambox/cgi-bin/status" | awk '/Standby/' | sed -e 's/<[^>]*>//g')" = "Standby:OFF" ] && DREAM_TIMEOUT=10 dreammessage dreambox "${SOURCE_DISP} is calling.${LF}${SOURCE_NAME}"
```

Of course, *dreambox* must be replaced with the host name or IP address
of the Dreambox, and password authentication must be included if needed.

*Source: [IPPF thread](http://www.ip-phone-forum.de/showthread.php?t=100706&page=55)*

## DreamBox with Enigma 2

```
  dream2message (default_dream2message)
```

`DREAM_TIMEOUT` and `DREAM_ICON` are also supported here.

Example of a popup that shows only the name, if present in Callers, and
the caller's phone number:

```
in:request ^ ^ dream2message 192.168.178.25 "${SOURCE_NAME} ${SOURCE} is calling."
```

## Email Notification

The function `mailmessage` sends an email using the data configured for
the push service, unless something else is specified when calling it
(mailer options). The push service itself can remain disabled; the
important part is the settings for addresses, mail server, and so on.
Examples for use in listeners:

```
mailmessage
mailmessage -t me@my.self
mailmessage -s "Oh, oh ... ($SOURCE)"
```

-   Mail addresses, server settings, passwords, and so on are taken from
    the FritzBox push service configuration. Individual parts can be
    overridden by options, for example the destination address with `-t`
    in the example.
-   The options are passed through to `mail`, which in turn passes most of
    them on to `mailer`. Therefore, the following options can be used:

    ```
      -s STRING          - Subject. ("FRITZ!Box")
      -f STRING          - From. (NULL)
      -t STRING          - To. (NULL)
      -m STRING          - mailserver. (NULL)
      -a STRING          - authname. (NULL)
      -w STRING          - passwd. (NULL)
      -d STRING          - attachment. (NULL)
      -i STRING          - inline attachment. (NULL)
    ```

-   To customize mails, see `mail_subject` and `mail_body` in `mail.sh`.
    For overwriting, it is best to use
    `/tmp/flash/callmonitor/actions.local.d/`; see customizing
    notification texts.

## mail

`mail` is a script for temporarily storing mails when mail server errors
occur and sending them again later. All parameters and attachments are
packed and stored in `/var/spool/mail/`.

-   It is used by the mailmessage action.
-   You should regularly run `mail process`, for example with cron, to
    send any waiting mail.
-   Strictly speaking, `mail` does not necessarily belong to the
    Callmonitor, because other services might also need it. Perhaps in
    the future it will become its own package.

## Replacement for mail_missed_call

The function `mail_missed_call` no longer exists since version 1.0. It is
replaced by a general email notification function (`mailmessage`) that can
also be used together with the `in:cancel` event to send mail for missed
calls:

```
in:cancel   ^   ^   mailmessage
```

The nice thing is that the mail is sent immediately when the calling
party gives up; there is no longer a wait time of one minute as in
previous versions. In addition, it can now be determined more reliably
when a call was missed.

Of course, this way you can also receive mail about all incoming calls,
or about all outgoing calls to a specific number, and so on.

## DGStation Relook 400S

The [DGStation Relook 400S](http://www.dgstation.co.kr) supports only the
display of a short line without umlauts. The display duration can be
influenced through the environment variable `RELOOK_TIMEOUT`, in seconds.

```
  relookmessage (default_relookmessage)
```

Example of use with changed display duration (25 seconds):

```
  RELOOK_TIMEOUT=25 relookmessage 192.168.34.56
```

## Simple TCP Connections (rawmsg)

```
  Usage: rawmsg [OPTION]... <HOST> <template> [<param>]...
         rawmsg [OPTION]... -t <template> <host> [<param>]...
  Send a message over a plain TCP connection.

    -t, --template=FORMAT  use this printf-style template to build the message,
                           all following parameters are filled in
    -d, --default=CODE     default for first parameter (eval'ed later)
    -p, --port=PORT        use a special target port (default 80)
    -w, --timeout=SECONDS  set connect timeout (default 3)
        --help             show this help
```

The **following functions are based** on `rawmsg` and therefore support
the same options. The URL template (`-t`), the default message (`-d`), and
the port (`-p`) are already preset appropriately for the respective
receiver.

## Wake on LAN

The `ether-wake` program included in Freetz is used to wake a computer in
the LAN, provided the computer generally supports this. For usage, see
its online help:

```
Usage: ether-wake [-b] [-i iface] [-p aa:bb:cc:dd[:ee:ff]] MAC

Send a magic packet to wake up sleeping machines.
MAC must be a station address (00:11:22:33:44:55) or
    a hostname with a known 'ethers' entry.

Options:
        -b              Send wake-up packet to the broadcast address
        -i iface        Use interface ifname instead of the default "eth0"
        -p pass Append the four or six byte password PW to the packet
```

## Maintenance

The maintenance page in the web interface provides the following:

-   Clean up phone book: sorts the phone book entries and removes blank
    lines.
-   Perform SIP update: creates default entries in the phone book for new
    internet phone numbers.
-   Enable/disable Callmonitor interface (port 1012): enables or disables
    the Callmonitor interface on port 1012. The Callmonitor works only
    with the interface enabled.

The maintenance page can be found in the Freetz web interface under
*Extras => Maintenance*.

[![[Callmonitor: maintenance]](../../docs/screenshots/24_md.png)](../../docs/screenshots/24.png)

## Reverse Lookup

Reverse lookup is configured in the Callmonitor basic configuration. It
is performed using one of the following services:

-   [http://telefonbuch.de/](http://telefonbuch.de/)
-   [http://inverssuche.de/](http://inverssuche.de/)
-   [http://goyellow.de/](http://goyellow.de/)
-   [http://11880.com/](http://11880.com/)
-   [http://www.dasoertliche.de/](http://www.dasoertliche.de/)
-   [http://tel.search.ch/](http://tel.search.ch/)
-   [http://www.das-telefonbuch.at/](http://www.das-telefonbuch.at/)
-   [http://www.anywho.com/](http://www.anywho.com/)

Optionally, an additional Google search for the caller's local area can
be performed. The result of this search is used only if the full reverse
lookup returns no result.

-   For outgoing calls, a request is made for the called number if
    necessary, not for one's own number.
-   Reverse lookup is possible with permanent caching in flash, temporary
    caching in RAM, or no caching.

[![[Callmonitor: reverse lookup]](../../docs/screenshots/23_md.png)](../../docs/screenshots/23.png)

## Test Call

After the listeners are defined, it is recommended to test whether they
work correctly. Since not every configuration can always be tested with
real calls, there is a page in the web interface that simulates calls. No
telephones ring; the CallMonitor is merely presented with a simulated
call, which it handles like a real call.

[![[Callmonitor: test call]](../../docs/screenshots/22_md.png)](../../docs/screenshots/22.png)

The form should be mostly self-explanatory. Under "Event", set which
event should be simulated. The source phone number is the one from which
this event originates, and the destination phone number is the event's
target. Enter an event with phone numbers that match a pattern defined in
the listeners. After clicking "Test call", the Callmonitor should execute
the action belonging to this listener entry. The web interface displays
the Callmonitor debug information, which can help with troubleshooting.

## Callmonitor FAQ

- Can I also see the result of reverse lookup on my DECT telephone?

No. There is currently no known way to intervene in call signaling over
DECT.

## Customizing Notification Texts

To adapt the content of a notification to your own needs, use the
following approach:

1.  Create the directory `/tmp/flash/callmonitor/actions.local.d`.
2.  Create a file `foobar.sh` in it, or anything else with the `.sh`
    suffix.
3.  Copy only the function to be overwritten into it, for example
    `mail_body() { ... }`, and adapt it; or set only variables such as
    `RELOOK_TIMEOUT`.
4.  Call `modsave flash` to save the file in flash.
5.  Restart Callmonitor.

For most actions, a function `default_foomessage` is provided that
creates the default message for this action type. This function can
therefore simply be overwritten. For mailmessage/mail, for example, there
are `mail_subject` and `mail_body`; for other actions, only a look at the
source code, or a question, helps until their functions are also described
in the wiki.
