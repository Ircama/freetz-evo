/*
 * ja11-boot.c
 *
 * Puts a FiiO/JadeAudio JA11 (KT1213 chip) into firmware-update (boot) mode.
 *
 * Mechanism reverse-engineered from the official FiiO web app
 * (fiiocontrol.fiio.com, module kt1213-update-DEc7-1fu.js):
 *
 *   1. Send HID OUTPUT report ID 0x54 with payload "12345678\0"
 *      (bytes 31 32 33 34 35 36 37 38 00)  ->  updateBeforeReset()
 *   2. The device resets and re-enumerates as a USB CDC / serial port
 *      (VID 0x8888, 9600 baud).  ->  updateModeConnect()
 *   3. The firmware is then flashed over that serial port with the
 *      KT-family bootloader protocol (SYNC ".KTM", CHP, CFG, PWO, KSTA,
 *      write frames with CRC32, STP).
 *
 * This tool only performs step 1 (enter boot mode). No physical button is
 * needed. After running it, check the new enumeration (e.g. dmesg / lsusb /
 * /sys/class/tty) — the JA11 should appear as a serial device VID 0x8888.
 *
 * Build (libusb backend, no kernel HID/INPUT support required — works on
 * FritzBox via usbfs):
 *   gcc -Wall -O2 ja11-boot.c -lhidapi-libusb -o ja11-boot
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <unistd.h>
#include <getopt.h>
#include <hidapi/hidapi.h>

#define JA11_VID     0x2972
#define JA11_PID     0x0102

#define BOOT_REPORT_ID   0x54
#define BOOT_PAYLOAD     "12345678\0"   /* 9 bytes: "12345678" + NUL */
#define BOOT_PAYLOAD_LEN 9

/* Print a hidapi wide error string to stderr */
static void print_hid_error(hid_device *h)
{
    const wchar_t *err = h ? hid_error(h) : NULL;
    char buf[256];
    if (err && wcstombs(buf, err, sizeof(buf) - 1) != (size_t)-1) {
        buf[sizeof(buf) - 1] = 0;
        fprintf(stderr, "  hid error: %s\n", buf);
    }
}

static void list_devices(void)
{
    struct hid_device_info *devs, *cur;

    devs = hid_enumerate(0, 0);
    if (!devs) {
        printf("No HID devices found.\n");
        return;
    }
    for (cur = devs; cur; cur = cur->next) {
        char man[128] = "", prod[128] = "", ser[128] = "";
        if (cur->manufacturer_string)
            wcstombs(man, cur->manufacturer_string, sizeof(man) - 1);
        if (cur->product_string)
            wcstombs(prod, cur->product_string, sizeof(prod) - 1);
        if (cur->serial_number)
            wcstombs(ser, cur->serial_number, sizeof(ser) - 1);
        printf("%04x:%04x  %s", cur->vendor_id, cur->product_id, cur->path);
        if (prod[0])
            printf("  %s", prod);
        if (man[0])
            printf("  [%s]", man);
        if (ser[0])
            printf("  sn=%s", ser);
        printf("\n");
    }
    hid_free_enumeration(devs);
}

static void usage(const char *prog)
{
    printf(
        "Usage: %s [options]\n"
        "\n"
        "Puts the FiiO/JadeAudio JA11 (KT1213) into firmware-update (boot) mode\n"
        "by sending HID output report ID 0x54 with payload \"12345678\\0\".\n"
        "Afterwards the device re-enumerates as a USB CDC serial port\n"
        "(VID 0x8888, 9600 baud) for firmware flashing.\n"
        "\n"
        "Options:\n"
        "  -l, --list       list HID devices and exit\n"
        "  -c, --check      open the device and close it WITHOUT sending the\n"
        "                   boot trigger (safe connection test)\n"
        "  -v, --vid HEX    vendor ID  (default 0x2972)\n"
        "  -p, --pid HEX    product ID (default 0x0102)\n"
        "  -h, --help       show this help\n",
        prog);
}

int main(int argc, char **argv)
{
    static const struct option longopts[] = {
        { "list",  no_argument,       NULL, 'l' },
        { "check", no_argument,       NULL, 'c' },
        { "vid",   required_argument, NULL, 'v' },
        { "pid",   required_argument, NULL, 'p' },
        { "help",  no_argument,       NULL, 'h' },
        { NULL, 0, NULL, 0 }
    };
    int do_list = 0, do_check = 0;
    unsigned int vid = JA11_VID, pid = JA11_PID;
    int opt;

    while ((opt = getopt_long(argc, argv, "lcv:p:h", longopts, NULL)) != -1) {
        switch (opt) {
        case 'l':
            do_list = 1;
            break;
        case 'c':
            do_check = 1;
            break;
        case 'v':
            vid = (unsigned int)strtoul(optarg, NULL, 0);
            break;
        case 'p':
            pid = (unsigned int)strtoul(optarg, NULL, 0);
            break;
        case 'h':
        default:
            usage(argv[0]);
            return opt == 'h' ? 0 : 1;
        }
    }

    if (hid_init())
        return 1;

    if (do_list) {
        list_devices();
        hid_exit();
        return 0;
    }

    hid_device *dev = hid_open(vid, pid, NULL);
    if (!dev) {
        fprintf(stderr, "Error: JA11 device %04x:%04x not found / cannot be opened.\n", vid, pid);
        fprintf(stderr, "  If the device is listed by -l but open fails, the HID interface may\n"
                        "  be held by another process (e.g. a lingering hidws bridge).\n"
                        "  On the FritzBox check: ps w | grep hid\n");
        print_hid_error(NULL);
        hid_exit();
        return 1;
    }
    printf("Opened %04x:%04x\n", vid, pid);

    if (do_check) {
        printf("Connection OK (device opened and closed without sending the trigger).\n");
        hid_close(dev);
        hid_exit();
        return 0;
    }

    /* Output report ID 0x54, payload "12345678\0" (updateBeforeReset). */
    uint8_t buf[1 + BOOT_PAYLOAD_LEN];
    buf[0] = BOOT_REPORT_ID;
    memcpy(buf + 1, BOOT_PAYLOAD, BOOT_PAYLOAD_LEN);

    printf("Sending HID output report 0x%02X: ", BOOT_REPORT_ID);
    for (size_t i = 0; i < BOOT_PAYLOAD_LEN; i++)
        printf("%02X ", buf[1 + i]);
    printf("\n");

    int res = hid_write(dev, buf, sizeof(buf));
    if (res < 0) {
        fprintf(stderr, "Error: failed to send report (hid_write = %d)\n", res);
        print_hid_error(dev);
        hid_close(dev);
        hid_exit();
        return 1;
    }
    printf("Sent %d bytes (report 0x%02X).\n", res, BOOT_REPORT_ID);

    hid_close(dev);
    hid_exit();

    printf("\nThe JA11 should now reset into update mode and re-enumerate as a\n"
           "USB CDC serial port (VID 0x8888, 9600 baud). Check with:\n"
           "  dmesg | tail\n  lsusb\n  ls /sys/class/tty/\n"
           "Then flash the firmware over that serial port.\n");
    return 0;
}
