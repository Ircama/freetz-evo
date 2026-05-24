/*
 * SPDX-FileCopyrightText: 2026 Espressif Systems (Shanghai) CO LTD
 *
 * SPDX-License-Identifier: Unlicense OR CC0-1.0
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

#define DEFAULT_SERIAL_DEVICE "/dev/ttyUSB0"
#define DEFAULT_BAUD_RATE 115200
#define HIGHER_BAUD_RATE 460800

static const char *chip_to_string(target_chip_t chip)
{
    switch (chip) {
    case ESP8266_CHIP: return "esp8266";
    case ESP32_CHIP: return "esp32";
    case ESP32S2_CHIP: return "esp32s2";
    case ESP32C3_CHIP: return "esp32c3";
    case ESP32S3_CHIP: return "esp32s3";
    case ESP32C2_CHIP: return "esp32c2";
    case ESP32C5_CHIP: return "esp32c5";
    case ESP32H2_CHIP: return "esp32h2";
    case ESP32C6_CHIP: return "esp32c6";
    case ESP32P4_CHIP: return "esp32p4";
    case ESP32C61_CHIP: return "esp32c61";
    default: return "unknown";
    }
}

static bool parse_chip_name(const char *name, target_chip_t *out)
{
    if (strcmp(name, "esp8266") == 0) {
        *out = ESP8266_CHIP;
    } else if (strcmp(name, "esp32") == 0) {
        *out = ESP32_CHIP;
    } else if (strcmp(name, "esp32s2") == 0) {
        *out = ESP32S2_CHIP;
    } else if (strcmp(name, "esp32c3") == 0) {
        *out = ESP32C3_CHIP;
    } else if (strcmp(name, "esp32s3") == 0) {
        *out = ESP32S3_CHIP;
    } else if (strcmp(name, "esp32c2") == 0) {
        *out = ESP32C2_CHIP;
    } else if (strcmp(name, "esp32c5") == 0) {
        *out = ESP32C5_CHIP;
    } else if (strcmp(name, "esp32h2") == 0) {
        *out = ESP32H2_CHIP;
    } else if (strcmp(name, "esp32c6") == 0) {
        *out = ESP32C6_CHIP;
    } else if (strcmp(name, "esp32p4") == 0) {
        *out = ESP32P4_CHIP;
    } else if (strcmp(name, "esp32c61") == 0) {
        *out = ESP32C61_CHIP;
    } else {
        return false;
    }

    return true;
}

static void print_usage(const char *prog)
{
    fprintf(stderr,
            "Usage: %s [OPTIONS] <addr1> <file1> [<addr2> <file2> ...]\n"
            "\n"
            "Options:\n"
            "  -p, --port <device>   Serial device (default: %s)\n"
            "  -b, --baud <rate>     Baud rate     (default: %d)\n"
            "  -c, --chip <name>     Expected chip (esp32c3, esp32s3, ...)\n"
            "  -m, --mode <mode>     GPIO mode: dtr-rts | gpio | none (default: dtr-rts)\n"
            "  -n, --no-stub         Use ROM bootloader instead of stub (stub is default)\n"
            "  -h, --help\n"
            "\n"
            "Examples:\n"
            "  %s 0x1000 bootloader.bin 0x8000 partition-table.bin 0x10000 app.bin\n"
            "  %s -p /dev/ttyACM0 -c esp32c3 0x0 bootloader.bin 0x8000 partition-table.bin 0x10000 app.bin\n",
            prog, DEFAULT_SERIAL_DEVICE, DEFAULT_BAUD_RATE, prog, prog);
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

int main(int argc, char *argv[])
{
    const char *device = DEFAULT_SERIAL_DEVICE;
    uint32_t baud_rate = DEFAULT_BAUD_RATE;
    linux_gpio_mode_t gpio_mode = LINUX_GPIO_DTR_RTS;
    bool use_stub = true;
    bool expected_chip_set = false;
    target_chip_t expected_chip = ESP_UNKNOWN_CHIP;

    static const struct option long_opts[] = {
        { "port", required_argument, NULL, 'p' },
        { "baud", required_argument, NULL, 'b' },
        { "chip", required_argument, NULL, 'c' },
        { "mode", required_argument, NULL, 'm' },
        { "no-stub", no_argument, NULL, 'n' },
        { "help", no_argument, NULL, 'h' },
        { NULL, 0, NULL, 0 }
    };

    int opt;
    while ((opt = getopt_long(argc, argv, "p:b:c:m:nh", long_opts, NULL)) != -1) {
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
        case 'c':
            if (!parse_chip_name(optarg, &expected_chip)) {
                fprintf(stderr, "Invalid chip '%s'\n", optarg);
                return 1;
            }
            expected_chip_set = true;
            break;
        case 'm':
            if (strcmp(optarg, "dtr-rts") == 0) {
                gpio_mode = LINUX_GPIO_DTR_RTS;
            } else if (strcmp(optarg, "gpio") == 0) {
                gpio_mode = LINUX_GPIO_GPIOD;
            } else if (strcmp(optarg, "none") == 0) {
                gpio_mode = LINUX_GPIO_NONE;
            } else {
                fprintf(stderr, "Unknown mode '%s'. Use: dtr-rts | gpio | none\n", optarg);
                return 1;
            }
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

    {
        int remaining = argc - optind;
        if (remaining == 0) {
            fprintf(stderr, "Error: no <addr> <file> pairs given.\n\n");
            print_usage(argv[0]);
            return 1;
        }
        if ((remaining % 2) != 0) {
            fprintf(stderr, "Error: odd number of remaining arguments - expected <addr> <file> pairs.\n\n");
            print_usage(argv[0]);
            return 1;
        }
    }

    printf("Serial device : %s\n", device);
    printf("Baud rate     : %" PRIu32 "\n", baud_rate);
    printf("GPIO mode     : %s\n",
           gpio_mode == LINUX_GPIO_DTR_RTS ? "dtr-rts" :
           gpio_mode == LINUX_GPIO_GPIOD ? "gpio" : "none");
    if (expected_chip_set) {
        printf("Expected chip : %s\n", chip_to_string(expected_chip));
    }
    printf("Connect mode  : %s\n", use_stub ? "stub" : "ROM bootloader");

    {
        esp_loader_t loader;
        esp_loader_error_t conn_err;
        linux_port_t port = {
            .port.ops = &linux_uart_ops,
            .device = device,
            .baudrate = baud_rate,
            .gpio_mode = gpio_mode,
        };

        if (gpio_mode == LINUX_GPIO_GPIOD) {
            port.gpio_chip_path = "/dev/gpiochip0";
            port.reset_pin = 2;
            port.boot_pin = 3;
        }

        if (esp_loader_init_uart(&loader, &port.port) != ESP_LOADER_SUCCESS) {
            return 1;
        }

        if (use_stub) {
            conn_err = connect_to_target_with_stub(&loader, baud_rate, HIGHER_BAUD_RATE);
        } else {
            conn_err = connect_to_target(&loader, HIGHER_BAUD_RATE);
        }

        if (conn_err != ESP_LOADER_SUCCESS) {
            return 1;
        }

        {
            target_chip_t detected_chip = esp_loader_get_target(&loader);
            printf("Detected chip : %s\n", chip_to_string(detected_chip));
            if (expected_chip_set && detected_chip != expected_chip) {
                fprintf(stderr, "Error: detected chip '%s' differs from expected '%s'\n",
                        chip_to_string(detected_chip), chip_to_string(expected_chip));
                return 1;
            }
        }

        {
            int num_pairs = (argc - optind) / 2;
            char **pair_args = argv + optind;
            int i;

            for (i = 0; i < num_pairs; i++) {
                const char *addr_str = pair_args[i * 2];
                const char *file_path = pair_args[i * 2 + 1];
                char *endptr;
                uint32_t addr = (uint32_t)strtoul(addr_str, &endptr, 0);
                size_t size = 0;
                uint8_t *buf;
                esp_loader_error_t err;

                if (*endptr != '\0') {
                    fprintf(stderr, "Error: invalid address '%s'\n", addr_str);
                    return 1;
                }

                buf = read_file(file_path, &size);
                if (!buf) {
                    return 1;
                }

                printf("\nFlashing '%s' at 0x%" PRIx32 " (%zu bytes)...\n", file_path, addr, size);
                err = flash_binary(&loader, buf, (uint32_t)size, addr);
                free(buf);

                if (err != ESP_LOADER_SUCCESS) {
                    fprintf(stderr, "Error: failed to flash '%s'\n", file_path);
                    return 1;
                }
            }
        }

        printf("\nAll done! Resetting target...\n");
        esp_loader_reset_target(&loader);
        esp_loader_deinit(&loader);
    }

    return 0;
}
