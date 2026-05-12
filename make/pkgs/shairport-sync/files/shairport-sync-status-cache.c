#include <ctype.h>
#include <errno.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#define FIELD_SIZE 1024
#define SMALL_FIELD_SIZE 256

struct status_cache {
	char state[SMALL_FIELD_SIZE];
	char active[SMALL_FIELD_SIZE];
	char title[FIELD_SIZE];
	char artist[FIELD_SIZE];
	char album[FIELD_SIZE];
	char client_name[FIELD_SIZE];
	char client_ip[SMALL_FIELD_SIZE];
	char volume[SMALL_FIELD_SIZE];
	char progress[SMALL_FIELD_SIZE];
	char updated[SMALL_FIELD_SIZE];
};

static volatile sig_atomic_t keep_running = 1;

static void stop_running(int signal_number) {
	(void)signal_number;
	keep_running = 0;
}

static int hex_value(int character) {
	if ((character >= '0') && (character <= '9')) {
		return character - '0';
	}
	character = tolower((unsigned char)character);
	if ((character >= 'a') && (character <= 'f')) {
		return character - 'a' + 10;
	}
	return -1;
}

static int hex_to_code(const char *hex, char *output) {
	int index;

	for (index = 0; index < 4; ++index) {
		int high = hex_value(hex[index * 2]);
		int low = hex_value(hex[index * 2 + 1]);
		if ((high < 0) || (low < 0)) {
			return -1;
		}
		output[index] = (char)((high << 4) | low);
	}
	output[4] = '\0';
	return 0;
}

static int base64_value(int character) {
	if ((character >= 'A') && (character <= 'Z')) {
		return character - 'A';
	}
	if ((character >= 'a') && (character <= 'z')) {
		return character - 'a' + 26;
	}
	if ((character >= '0') && (character <= '9')) {
		return character - '0' + 52;
	}
	if (character == '+') {
		return 62;
	}
	if (character == '/') {
		return 63;
	}
	return -1;
}

static size_t base64_decode(const char *input, unsigned char *output, size_t output_size) {
	int buffer = 0;
	int bits_collected = 0;
	size_t output_length = 0;

	while (*input != '\0') {
		int current = *input++;

		if (isspace((unsigned char)current)) {
			continue;
		}
		if (current == '=') {
			break;
		}
		current = base64_value(current);
		if (current < 0) {
			continue;
		}

		buffer = (buffer << 6) | current;
		bits_collected += 6;
		if (bits_collected >= 8) {
			bits_collected -= 8;
			if (output_length < output_size) {
				output[output_length++] = (unsigned char)((buffer >> bits_collected) & 0xff);
			}
		}
	}

	return output_length;
}

static void copy_field(char *destination, size_t destination_size, const unsigned char *source,
			size_t source_length) {
	if (destination_size == 0) {
		return;
	}
	if (source_length >= destination_size) {
		source_length = destination_size - 1;
	}
	memcpy(destination, source, source_length);
	destination[source_length] = '\0';
}

static void shell_quote(FILE *output, const char *value) {
	fputc('\'', output);
	while (*value != '\0') {
		if (*value == '\'') {
			fputs("'\\''", output);
		} else {
			fputc(*value, output);
		}
		++value;
	}
	fputc('\'', output);
}

static void update_timestamp(struct status_cache *cache) {
	time_t now = time(NULL);
	struct tm *tm_now = localtime(&now);

	if (tm_now == NULL) {
		cache->updated[0] = '\0';
		return;
	}
	strftime(cache->updated, sizeof(cache->updated), "%Y-%m-%d %H:%M:%S", tm_now);
}

static int write_status_file(const char *path, const struct status_cache *cache) {
	char temporary_path[1024];
	FILE *output;

	if (snprintf(temporary_path, sizeof(temporary_path), "%s.tmp", path) >= (int)sizeof(temporary_path)) {
		return -1;
	}

	output = fopen(temporary_path, "w");
	if (output == NULL) {
		return -1;
	}

	fputs("SHAIRPORT_SYNC_STATUS_STATE=", output);
	shell_quote(output, cache->state);
	fputc('\n', output);
	fputs("SHAIRPORT_SYNC_STATUS_ACTIVE=", output);
	shell_quote(output, cache->active);
	fputc('\n', output);
	fputs("SHAIRPORT_SYNC_STATUS_TITLE=", output);
	shell_quote(output, cache->title);
	fputc('\n', output);
	fputs("SHAIRPORT_SYNC_STATUS_ARTIST=", output);
	shell_quote(output, cache->artist);
	fputc('\n', output);
	fputs("SHAIRPORT_SYNC_STATUS_ALBUM=", output);
	shell_quote(output, cache->album);
	fputc('\n', output);
	fputs("SHAIRPORT_SYNC_STATUS_CLIENT_NAME=", output);
	shell_quote(output, cache->client_name);
	fputc('\n', output);
	fputs("SHAIRPORT_SYNC_STATUS_CLIENT_IP=", output);
	shell_quote(output, cache->client_ip);
	fputc('\n', output);
	fputs("SHAIRPORT_SYNC_STATUS_VOLUME=", output);
	shell_quote(output, cache->volume);
	fputc('\n', output);
	fputs("SHAIRPORT_SYNC_STATUS_PROGRESS=", output);
	shell_quote(output, cache->progress);
	fputc('\n', output);
	fputs("SHAIRPORT_SYNC_STATUS_UPDATED=", output);
	shell_quote(output, cache->updated);
	fputc('\n', output);

	if (fclose(output) != 0) {
		unlink(temporary_path);
		return -1;
	}

	if (rename(temporary_path, path) != 0) {
		unlink(temporary_path);
		return -1;
	}

	return 0;
}

static void clear_now_playing(struct status_cache *cache) {
	cache->title[0] = '\0';
	cache->artist[0] = '\0';
	cache->album[0] = '\0';
	cache->progress[0] = '\0';
	cache->volume[0] = '\0';
}

static void apply_item(struct status_cache *cache, const char *type_code, const char *item_code,
		const unsigned char *payload, size_t payload_length) {
	if (strcmp(type_code, "core") == 0) {
		if (strcmp(item_code, "minm") == 0) {
			copy_field(cache->title, sizeof(cache->title), payload, payload_length);
		} else if (strcmp(item_code, "asar") == 0) {
			copy_field(cache->artist, sizeof(cache->artist), payload, payload_length);
		} else if (strcmp(item_code, "asal") == 0) {
			copy_field(cache->album, sizeof(cache->album), payload, payload_length);
		}
		return;
	}

	if (strcmp(type_code, "ssnc") != 0) {
		return;
	}

	if (strcmp(item_code, "pbeg") == 0 || strcmp(item_code, "prsm") == 0 || strcmp(item_code, "pres") == 0) {
		strcpy(cache->state, "playing");
		strcpy(cache->active, "yes");
	} else if (strcmp(item_code, "paus") == 0) {
		strcpy(cache->state, "paused");
		strcpy(cache->active, "yes");
	} else if (strcmp(item_code, "pend") == 0 || strcmp(item_code, "pfls") == 0) {
		strcpy(cache->state, "stopped");
		strcpy(cache->active, "no");
		clear_now_playing(cache);
	} else if (strcmp(item_code, "abeg") == 0) {
		strcpy(cache->active, "yes");
		if (cache->state[0] == '\0') {
			strcpy(cache->state, "active");
		}
	} else if (strcmp(item_code, "aend") == 0) {
		strcpy(cache->active, "no");
		strcpy(cache->state, "idle");
	} else if (strcmp(item_code, "snam") == 0) {
		copy_field(cache->client_name, sizeof(cache->client_name), payload, payload_length);
	} else if (strcmp(item_code, "clip") == 0) {
		copy_field(cache->client_ip, sizeof(cache->client_ip), payload, payload_length);
	} else if (strcmp(item_code, "pvol") == 0) {
		copy_field(cache->volume, sizeof(cache->volume), payload, payload_length);
	} else if (strcmp(item_code, "prgr") == 0) {
		copy_field(cache->progress, sizeof(cache->progress), payload, payload_length);
	}
}

static int process_stream(FILE *input, const char *status_path, struct status_cache *cache) {
	char line[1024];

	while (keep_running && (fgets(line, sizeof(line), input) != NULL)) {
		char type_hex[9];
		char code_hex[9];
		char type_code[5];
		char item_code[5];
		size_t payload_length = 0;
		unsigned char *payload = NULL;

		if (sscanf(line, "<item><type>%8[0-9a-fA-F]</type><code>%8[0-9a-fA-F]</code><length>%zu</length>",
				type_hex, code_hex, &payload_length) != 3) {
			continue;
		}
		if ((hex_to_code(type_hex, type_code) != 0) || (hex_to_code(code_hex, item_code) != 0)) {
			continue;
		}

		if (payload_length > 0) {
			size_t encoded_length = 4 * ((payload_length + 2) / 3);
			char *encoded = NULL;

			if (fgets(line, sizeof(line), input) == NULL) {
				break;
			}
			if (strcmp(line, "<data encoding=\"base64\">\n") != 0) {
				continue;
			}

			payload = calloc(payload_length + 1, sizeof(unsigned char));
			encoded = calloc(encoded_length + 4, sizeof(char));
			if ((payload == NULL) || (encoded == NULL)) {
				free(payload);
				free(encoded);
				continue;
			}

			if (fgets(encoded, (int)encoded_length + 4, input) == NULL) {
				free(payload);
				free(encoded);
				break;
			}
			payload_length = base64_decode(encoded, payload, payload_length);
			free(encoded);

			if (fgets(line, sizeof(line), input) == NULL) {
				free(payload);
				break;
			}
		}

		apply_item(cache, type_code, item_code, payload, payload_length);
		update_timestamp(cache);
		write_status_file(status_path, cache);
		free(payload);
	}

	return ferror(input) ? -1 : 0;
}

int main(int argc, char **argv) {
	const char *fifo_path;
	const char *status_path;
	struct status_cache cache;

	if (argc != 3) {
		fprintf(stderr, "Usage: %s <metadata-fifo> <status-file>\n", argv[0]);
		return 1;
	}

	fifo_path = argv[1];
	status_path = argv[2];
	memset(&cache, 0, sizeof(cache));
	strcpy(cache.state, "idle");
	strcpy(cache.active, "no");
	update_timestamp(&cache);
	write_status_file(status_path, &cache);

	signal(SIGTERM, stop_running);
	signal(SIGINT, stop_running);

	while (keep_running) {
		FILE *input = fopen(fifo_path, "r");
		if (input == NULL) {
			if ((errno == ENOENT) || (errno == ENXIO)) {
				sleep(1);
				continue;
			}
			perror("fopen");
			sleep(1);
			continue;
		}

		process_stream(input, status_path, &cache);
		fclose(input);
	}

	return 0;
}