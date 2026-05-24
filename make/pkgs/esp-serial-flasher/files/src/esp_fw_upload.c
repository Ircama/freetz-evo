/*
 * SPDX-License-Identifier: Apache-2.0
 */

#include <getopt.h>
#include <inttypes.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "esp_loader.h"
#include "example_common.h"
#include "linux_port.h"

#define DEFAULT_SERIAL_DEVICE "/dev/ttyACM0"
#define DEFAULT_BAUD_RATE 115200
#define HIGHER_BAUD_RATE 460800

#define PARTITION_TABLE_ADDR 0x8000
#define APP_ADDR 0x10000

static void print_usage(const char *prog)
{
    fprintf(stderr,
            "Usage: %s [OPTIONS]\n"
            "\n"
            "Options:\n"
            "  -p, --port <device>       Serial device (default: %s)\n"
            "  -b, --baud <rate>         Baud rate (default: %d)\n"
            "  -B, --bootloader <file>   Bootloader image (default: bootloader.bin)\n"
            "  -T, --partition <file>    Partition table image (default: partition-table.bin)\n"
            "  -A, --app <file>          App image (default: ble50_scan.bin)\n"
            "  -n, --no-stub             Use ROM bootloader instead of stub\n"
            "  -h, --help\n"
            "\n"
            "Example:\n"
            "  %s -p /dev/ttyACM0 -B bootloader.bin -T partition-table.bin -A ble50_scan.bin\n",
            prog,
            DEFAULT_SERIAL_DEVICE,
            DEFAULT_BAUD_RATE,
            prog);
}

static uint8_t *read_file(const char *path, size_t *out_size)
{
    FILE *f = fopen(path, "rb");
    long len;
    uint8_t *buf;

    if (!f) {
        fprintf(stderr, "Error: cannot open file '%s'\n", path);
        return NULL;
    }

    fseek(f, 0, SEEK_END);
    len = ftell(f);
    fseek(f, 0, SEEK_SET);

    if (len <= 0) {
        fprintf(stderr, "Error: file '%s' is empty or unreadable\n", path);
        fclose(f);
        return NULL;
    }

    buf = malloc((size_t)len);
    if (!buf) {
        fprintf(stderr, "Error: out of memory\n");
        fclose(f);
        return NULL;
    }

    if (fread(buf, 1, (size_t)len, f) != (size_t)len) {
        fprintf(stderr, "Error: could not read file '%s'\n", path);
        free(buf);
        fclose(f);
        return NULL;
    }

    fclose(f);
    *out_size = (size_t)len;
    return buf;
}

static esp_loader_error_t flash_file(esp_loader_t *loader, const char *path, uint32_t address)
{
    size_t size = 0;
    uint8_t *buf = read_file(path, &size);
    esp_loader_error_t err;

    if (!buf) {
        return ESP_LOADER_ERROR_FAIL;
    }

    printf("\nFlashing '%s' at 0x%" PRIx32 " (%zu bytes)...\n", path, address, size);
    err = flash_binary(loader, buf, size, address);
    free(buf);

    if (err != ESP_LOADER_SUCCESS) {
        fprintf(stderr, "Error: failed to flash '%s'\n", path);
    }

    return err;
}

int main(int argc, char *argv[])
{
    const char *device = DEFAULT_SERIAL_DEVICE;
    const char *bootloader = "bootloader.bin";
    const char *partition = "partition-table.bin";
    const char *app = "ble50_scan.bin";
    uint32_t baud_rate = DEFAULT_BAUD_RATE;
    bool use_stub = true;

    static const struct option long_opts[] = {
        { "port", required_argument, NULL, 'p' },
        { "baud", required_argument, NULL, 'b' },
        { "bootloader", required_argument, NULL, 'B' },
        { "partition", required_argument, NULL, 'T' },
        { "app", required_argument, NULL, 'A' },
        { "no-stub", no_argument, NULL, 'n' },
        { "help", no_argument, NULL, 'h' },
        { NULL, 0, NULL, 0 }
    };

    int opt;
    esp_loader_t loader;
    linux_port_t port;
    esp_loader_error_t err;
    uint32_t bootloader_addr;

    while ((opt = getopt_long(argc, argv, "p:b:B:T:A:nh", long_opts, NULL)) != -1) {
        switch (opt) {
        case 'p':
            device = optarg;
            break;
        case 'b':
            baud_rate = (uint32_t)strtoul(optarg, NULL, 10);
            if (baud_rate == 0) {
                fprintf(stderr, "Invalid baud rate: %s\n", optarg);
                return 1;
            }
            break;
        case 'B':
            bootloader = optarg;
            break;
        case 'T':
            partition = optarg;
            break;
        case 'A':
            app = optarg;
            break;
        case 'n':
            use_stub = false;
            break;
        case 'h':
            print_usage(argv[0]);
            return 0;
        default:
            print_usage(argv[0]);
            return 1;
        }
    }

    printf("Serial device : %s\n", device);
    printf("Baud rate     : %" PRIu32 "\n", baud_rate);
    printf("Connect mode  : %s\n", use_stub ? "stub" : "ROM bootloader");

    port = (linux_port_t) {
        .port.ops = &linux_uart_ops,
        .device = device,
        .baudrate = baud_rate,
        .gpio_mode = LINUX_GPIO_DTR_RTS,
    };

    err = esp_loader_init_uart(&loader, &port.port);
    if (err != ESP_LOADER_SUCCESS) {
        return 1;
    }

    if (use_stub) {
        err = connect_to_target_with_stub(&loader, baud_rate, HIGHER_BAUD_RATE);
    } else {
        err = connect_to_target(&loader, HIGHER_BAUD_RATE);
    }
    if (err != ESP_LOADER_SUCCESS) {
        esp_loader_deinit(&loader);
        return 1;
    }

    bootloader_addr = get_bootloader_address(esp_loader_get_target(&loader));

    if (flash_file(&loader, bootloader, bootloader_addr) != ESP_LOADER_SUCCESS ||
        flash_file(&loader, partition, PARTITION_TABLE_ADDR) != ESP_LOADER_SUCCESS ||
        flash_file(&loader, app, APP_ADDR) != ESP_LOADER_SUCCESS) {
        esp_loader_deinit(&loader);
        return 1;
    }

    printf("\nAll done! Resetting target...\n");
    esp_loader_reset_target(&loader);
    esp_loader_deinit(&loader);

    return 0;
}
