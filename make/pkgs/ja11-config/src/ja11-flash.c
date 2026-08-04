/*
 * ja11-flash.c
 *
 * Flashes a FiiO/JadeAudio JA11 (KT021/KT1213 chip) firmware over the USB CDC
 * serial port. The device must ALREADY be in update (boot) mode: VID:PID
 * 8888:cdc0, "KT Virtual Com Port", typically /dev/ttyACM0 or /dev/ttyACM1.
 * To get there, run ja11-boot (sends HID output report 0x54 "12345678\0").
 *
 * Protocol ported faithfully from the official FiiO web app
 * (fiiocontrol.fiio.com, module kt1213-update-DEc7-1fu.js, function se()):
 *
 *   1. write SYNC ".KTM" 1E 4B 54 4D        (wait 300ms)
 *   2. write CHP         D2 43 48 50        (wait 300ms)
 *   3. write CFG         2D 29 00 10 0E 15 00 60 00 BC   (wait 600ms)
 *   4. write PWO         3C 50 57 4F        (wait 300ms)
 *   5. write KSTA        4B 53 54 41
 *   6. for each frame: (wait 100ms) write frame
 *        frame = [69][burnSize lo][(eraseNum&7)<<5 | burnSize hi5][addr 24-bit LE]
 *                + data + CRC32-LE (init 0, reflected table, no final xor)
 *        block size 1024, eraseNum = (block%32==0)?1:7
 *        base address = fw[15]==1 ? 0x8000 : 0 ; first 16 bytes written as the
 *        final block at base, data blocks start at base+16
 *   7. (wait 300ms) write STP 96 53 54 50  (wait 300ms)
 *   8. write "ZRST" 5A 52 53 54, read reply, expect first byte 0x78 (ACK)
 *
 * Build (runs on the FritzBox, MIPS/uClibc):
 *   gcc -Wall -O2 ja11-flash.c -o ja11-flash
 *
 * Usage:
 *   ja11-flash /dev/ttyACM1 firmware.bin
 *
 * WARNING: flashing the wrong firmware can BRICK the device. Only use a
 * firmware meant for the JA11.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <unistd.h>
#include <fcntl.h>
#include <termios.h>
#include <errno.h>
#include <poll.h>

/* ---- protocol constants (from kt1213-update-DEc7-1fu.js) ---- */

static const uint8_t CMD_SYNC[] = { 0x1E, 0x4B, 0x54, 0x4D }; /* ".KTM" */
static const uint8_t CMD_CHP[]  = { 0xD2, 0x43, 0x48, 0x50 };
static const uint8_t CMD_CFG[]  = { 0x2D, 0x29, 0x00, 0x10, 0x0E, 0x15, 0x00, 0x60, 0x00, 0xBC };
static const uint8_t CMD_PWO[]  = { 0x3C, 0x50, 0x57, 0x4F };
static const uint8_t CMD_KSTA[] = { 0x4B, 0x53, 0x54, 0x41 };
static const uint8_t CMD_STP[]  = { 0x96, 0x53, 0x54, 0x50 };
static const uint8_t CMD_ZRST[] = { 0x5A, 0x52, 0x53, 0x54 }; /* final reset */

#define ACK_BYTE        0x78

#define FRAME_CMD       0x69
#define BLOCK_SIZE      1024
#define ERASE_MODULUS   32
#define BASE_MULT       0x8000    /* g*32 = 1024*32 */

#define DELAY_MS        300

/* ---- CRC32 (frame variant: init 0, reflected table, no final xor, LE) ---- */

static uint32_t crc_table[256];

static void crc_init(void)
{
    uint32_t i, k;
    for (i = 0; i < 256; i++) {
        uint32_t c = i;
        for (k = 0; k < 8; k++)
            c = (c & 1) ? (c >> 1) ^ 0xEDB88320u : (c >> 1);
        crc_table[i] = c;
    }
}

/* Compute the frame CRC over (len-4) bytes and store it LE at data+len-4. */
static void frame_crc(uint8_t *data, size_t len)
{
    uint32_t t = 0;
    size_t n = len - 4, i;
    for (i = 0; i < n; i++)
        t = crc_table[(t ^ data[i]) & 0xFF] ^ (t >> 8);
    data[n]     = (uint8_t)(t & 0xFF);
    data[n + 1] = (uint8_t)((t >> 8) & 0xFF);
    data[n + 2] = (uint8_t)((t >> 16) & 0xFF);
    data[n + 3] = (uint8_t)((t >> 24) & 0xFF);
}

/* ---- frame builders (port of Rt() and St()) ---- */

/* 6-byte header: [cmd][burnSize lo][(eraseNum&7)<<5 | burnSize hi5][addr 24-bit LE] */
static void header_6(uint8_t *out, uint8_t cmd, unsigned int burnSize,
                     uint8_t eraseNum, uint32_t addr)
{
    out[0] = cmd;
    out[1] = (uint8_t)(burnSize & 0xFF);
    out[2] = (uint8_t)(((eraseNum & 7) << 5) | ((burnSize >> 8) & 0x1F));
    out[3] = (uint8_t)(addr & 0xFF);
    out[4] = (uint8_t)((addr >> 8) & 0xFF);
    out[5] = (uint8_t)((addr >> 16) & 0xFF);
}

/* Data frame for block idx (port of Rt with e=ERASE_MODULUS). */
static size_t build_data_frame(const uint8_t *fw, size_t fw_len, uint32_t base,
                               size_t idx, uint8_t *out)
{
    size_t a, s, c;
    unsigned int burnSize;
    uint8_t eraseNum;
    uint32_t addr;

    if (idx == 0) {
        /* block 0: data starts at firmware offset 16, flash addr base+16,
         * size min(1024, fw_len) (port of: a=16, s=Math.min(1024,len),
         * i.addr=16+r) */
        a = 16;
        s = (BLOCK_SIZE < fw_len) ? BLOCK_SIZE : fw_len;
        addr = 16 + base;
    } else {
        a = idx * BLOCK_SIZE;
        s = (a + BLOCK_SIZE < fw_len) ? a + BLOCK_SIZE : fw_len;
        addr = (uint32_t)(idx * BLOCK_SIZE + base);
    }
    c = s - a;
    burnSize = (c > BLOCK_SIZE) ? BLOCK_SIZE : c;
    eraseNum = (idx % ERASE_MODULUS == 0) ? 1 : 7;

    header_6(out, FRAME_CMD, burnSize, eraseNum, addr);
    memcpy(out + 6, fw + a, c);
    frame_crc(out, 6 + c + 4);
    return 6 + c + 4;
}

/* Final block: writes the first 16 firmware bytes at base (port of St()). */
static size_t build_final_block(const uint8_t *fw, uint32_t base, uint8_t *out)
{
    header_6(out, FRAME_CMD, 16, 7, base);
    memcpy(out + 6, fw, 16);
    frame_crc(out, 6 + 16 + 4);
    return 6 + 16 + 4;
}

/* ---- serial I/O ---- */

static int open_serial(const char *path, int *fd_out)
{
    int fd;
    struct termios tio;

    fd = open(path, O_RDWR | O_NOCTTY | O_NONBLOCK);
    if (fd < 0) {
        fprintf(stderr, "Error: cannot open %s: %s\n", path, strerror(errno));
        return -1;
    }
    if (tcgetattr(fd, &tio) < 0) {
        fprintf(stderr, "Error: tcgetattr: %s\n", strerror(errno));
        close(fd);
        return -1;
    }
    cfmakeraw(&tio);
    tio.c_cflag &= ~(CSIZE | PARENB);
    tio.c_cflag |= CS8 | CLOCAL | CREAD;
    tio.c_cflag &= ~CSTOPB;
    cfsetispeed(&tio, B9600);
    cfsetospeed(&tio, B9600);
    tio.c_cc[VMIN] = 0;
    tio.c_cc[VTIME] = 1;   /* 100ms read timeout */
    if (tcsetattr(fd, TCSANOW, &tio) < 0) {
        fprintf(stderr, "Error: tcsetattr: %s\n", strerror(errno));
        close(fd);
        return -1;
    }
    /* restore blocking mode (clear O_NONBLOCK) */
    fcntl(fd, F_SETFL, fcntl(fd, F_GETFL) & ~O_NONBLOCK);
    *fd_out = fd;
    return 0;
}

static int write_all(int fd, const uint8_t *buf, size_t len)
{
    size_t off = 0;
    while (off < len) {
        ssize_t n = write(fd, buf + off, len - off);
        if (n < 0) {
            if (errno == EINTR)
                continue;
            fprintf(stderr, "Error: serial write: %s\n", strerror(errno));
            return -1;
        }
        off += (size_t)n;
    }
    return 0;
}

static void msleep(unsigned ms)
{
    usleep((useconds_t)ms * 1000);
}

/* Read up to len bytes, waiting up to timeout_ms; returns bytes read. */
static int read_with_timeout(int fd, uint8_t *buf, size_t len, int timeout_ms)
{
    struct pollfd pfd;
    size_t got = 0;
    int remaining = timeout_ms;

    while (got < len && remaining > 0) {
        pfd.fd = fd;
        pfd.events = POLLIN;
        int rc = poll(&pfd, 1, remaining);
        if (rc < 0) {
            if (errno == EINTR)
                continue;
            break;
        }
        if (rc == 0)
            break;   /* timeout */
        ssize_t n = read(fd, buf + got, len - got);
        if (n < 0) {
            if (errno == EINTR)
                continue;
            break;
        }
        if (n == 0)
            break;
        got += (size_t)n;
        remaining = timeout_ms - (int)got;
    }
    return (int)got;
}

/* ---- flash sequence (port of se()) ---- */

static int flash(int fd, const uint8_t *fw, size_t fw_len, int progress)
{
    uint8_t *frames;
    size_t *frame_lens;
    size_t cap, off = 0;
    size_t n_data_blocks, nframes;
    uint32_t base;
    uint8_t reply[64];
    int n, ok = 0;

    if (fw_len < 16) {
        fprintf(stderr, "Error: firmware too small (%zu bytes)\n", fw_len);
        return 0;
    }

    base = (fw[15] == 1) ? BASE_MULT : 0;
    n_data_blocks = (fw_len + BLOCK_SIZE - 1) / BLOCK_SIZE;
    nframes = n_data_blocks + 1;

    /* Allocate worst-case buffer: blocks (6+1024+4 each) + final (6+16+4) */
    cap = n_data_blocks * (6 + BLOCK_SIZE + 4) + (6 + 16 + 4);
    frames = malloc(cap);
    frame_lens = malloc(nframes * sizeof(size_t));
    if (!frames || !frame_lens) {
        fprintf(stderr, "Error: out of memory\n");
        free(frames);
        free(frame_lens);
        return 0;
    }

    for (size_t i = 0; i < n_data_blocks; i++) {
        frame_lens[i] = build_data_frame(fw, fw_len, base, i, frames + off);
        off += frame_lens[i];
    }
    frame_lens[n_data_blocks] = build_final_block(fw, base, frames + off);
    off += frame_lens[n_data_blocks];
    printf("Firmware: %zu bytes, %zu data blocks, base 0x%04X\n",
           fw_len, n_data_blocks, base);

    if (progress) printf("  sync\n");
    if (write_all(fd, CMD_SYNC, sizeof(CMD_SYNC)) < 0) goto fail;
    msleep(DELAY_MS);

    if (write_all(fd, CMD_CHP, sizeof(CMD_CHP)) < 0) goto fail;
    msleep(DELAY_MS);

    if (write_all(fd, CMD_CFG, sizeof(CMD_CFG)) < 0) goto fail;
    msleep(DELAY_MS);
    msleep(DELAY_MS);

    if (write_all(fd, CMD_PWO, sizeof(CMD_PWO)) < 0) goto fail;
    msleep(DELAY_MS);

    if (write_all(fd, CMD_KSTA, sizeof(CMD_KSTA)) < 0) goto fail;

    off = 0;
    for (size_t i = 0; i < nframes; i++) {
        msleep(100);
        if (write_all(fd, frames + off, frame_lens[i]) < 0) goto fail;
        off += frame_lens[i];
        if (progress && (i + 1) % 10 == 0)
            printf("  block %zu/%zu\n", i + 1, nframes);
    }
    if (progress) printf("  %zu blocks written\n", nframes);

    msleep(DELAY_MS);
    if (write_all(fd, CMD_STP, sizeof(CMD_STP)) < 0) goto fail;
    msleep(DELAY_MS);

    if (write_all(fd, CMD_ZRST, sizeof(CMD_ZRST)) < 0) goto fail;
    n = read_with_timeout(fd, reply, sizeof(reply), 2000);
    if (n > 0 && reply[0] == ACK_BYTE) {
        printf("Done: ACK 0x%02X received.\n", reply[0]);
        ok = 1;
    } else {
        fprintf(stderr, "FAIL: final reset not ACKed (reply=%d bytes). "
                        "Device may need a re-plug and retry.\n", n);
    }

fail:
    free(frames);
    free(frame_lens);
    return ok;
}

static void usage(const char *prog)
{
    printf(
        "Usage: %s <serial-port> <firmware.bin>\n"
        "\n"
        "Flash a FiiO/JadeAudio JA11 firmware over the USB CDC serial port.\n"
        "The device must already be in update mode (VID:PID 8888:cdc0, \"KT\n"
        "Virtual Com Port\", usually /dev/ttyACM0 or /dev/ttyACM1, 9600 baud).\n"
        "To enter update mode use the ja11-boot tool.\n"
        "\n"
        "Example:\n"
        "  %s /dev/ttyACM1 firmware/JadeAudio_JA11_V2.2.bin\n"
        "\n"
        "WARNING: flashing the wrong firmware can brick the device.\n",
        prog, prog);
}

int main(int argc, char **argv)
{
    const char *port, *fw_path;
    FILE *f;
    long fw_len;
    uint8_t *fw = NULL;
    int fd;
    int ret = 1;

    if (argc != 3) {
        usage(argv[0]);
        return 1;
    }
    port = argv[1];
    fw_path = argv[2];

    f = fopen(fw_path, "rb");
    if (!f) {
        fprintf(stderr, "Error: cannot open %s\n", fw_path);
        return 1;
    }
    fseek(f, 0, SEEK_END);
    fw_len = ftell(f);
    fseek(f, 0, SEEK_SET);
    if (fw_len <= 0) {
        fprintf(stderr, "Error: firmware file is empty\n");
        fclose(f);
        return 1;
    }
    fw = malloc((size_t)fw_len);
    if (!fw) {
        fprintf(stderr, "Error: out of memory\n");
        fclose(f);
        return 1;
    }
    if (fread(fw, 1, (size_t)fw_len, f) != (size_t)fw_len) {
        fprintf(stderr, "Error: short read from %s\n", fw_path);
        free(fw);
        fclose(f);
        return 1;
    }
    fclose(f);

    if (open_serial(port, &fd) < 0) {
        free(fw);
        return 1;
    }
    printf("Opened %s (9600 8N1)\n", port);

    crc_init();
    ret = flash(fd, fw, (size_t)fw_len, 1) ? 0 : 1;

    close(fd);
    free(fw);
    return ret;
}
