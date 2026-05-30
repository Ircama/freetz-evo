#include <curl/curl.h>

#include <ctype.h>
#include <dirent.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#define MELCLOUD_DEFAULT_BASE_URL "https://app.melcloud.com/Mitsubishi.Wifi.Client"
#define MELCLOUD_DEFAULT_APP_VERSION "1.34.13.0"
#define MELCLOUD_DEFAULT_TEMPLATE_DIR "/tmp/flash/melcloud/templates"
#define MELCLOUD_DEFAULT_SESSION_FILE "/tmp/flash/melcloud/session.key"

struct strbuf {
    char *data;
    size_t len;
    size_t cap;
};

static void strbuf_init(struct strbuf *b) {
    b->data = NULL;
    b->len = 0;
    b->cap = 0;
}

static int strbuf_reserve(struct strbuf *b, size_t need) {
    if (need <= b->cap) {
        return 0;
    }
    size_t new_cap = b->cap ? b->cap : 256;
    while (new_cap < need) {
        new_cap *= 2;
    }
    char *p = (char *)realloc(b->data, new_cap);
    if (!p) {
        return -1;
    }
    b->data = p;
    b->cap = new_cap;
    return 0;
}

static int strbuf_append_n(struct strbuf *b, const char *s, size_t n) {
    if (strbuf_reserve(b, b->len + n + 1) != 0) {
        return -1;
    }
    memcpy(b->data + b->len, s, n);
    b->len += n;
    b->data[b->len] = '\0';
    return 0;
}

static int strbuf_append(struct strbuf *b, const char *s) {
    return strbuf_append_n(b, s, strlen(s));
}

static void strbuf_free(struct strbuf *b) {
    free(b->data);
    b->data = NULL;
    b->len = 0;
    b->cap = 0;
}

static size_t curl_write_cb(void *ptr, size_t size, size_t nmemb, void *userdata) {
    size_t total = size * nmemb;
    struct strbuf *out = (struct strbuf *)userdata;
    if (strbuf_append_n(out, (const char *)ptr, total) != 0) {
        return 0;
    }
    return total;
}

static const char *arg_value(int argc, char **argv, const char *name) {
    int i;
    for (i = 2; i < argc - 1; ++i) {
        if (strcmp(argv[i], name) == 0) {
            return argv[i + 1];
        }
    }
    return NULL;
}

static int ensure_dir(const char *path) {
    struct stat st;
    if (stat(path, &st) == 0) {
        return S_ISDIR(st.st_mode) ? 0 : -1;
    }
    if (mkdir(path, 0755) != 0 && errno != EEXIST) {
        return -1;
    }
    return 0;
}

static int ensure_parent_dir(const char *file_path) {
    char *tmp = strdup(file_path);
    if (!tmp) {
        return -1;
    }
    char *slash = strrchr(tmp, '/');
    if (!slash) {
        free(tmp);
        return 0;
    }
    *slash = '\0';
    if (tmp[0] == '\0') {
        free(tmp);
        return 0;
    }
    int rc = ensure_dir(tmp);
    free(tmp);
    return rc;
}

static int read_text_file(const char *path, struct strbuf *out) {
    FILE *f = fopen(path, "rb");
    if (!f) {
        return -1;
    }
    char buf[4096];
    size_t n;
    strbuf_init(out);
    while ((n = fread(buf, 1, sizeof(buf), f)) > 0) {
        if (strbuf_append_n(out, buf, n) != 0) {
            fclose(f);
            strbuf_free(out);
            return -1;
        }
    }
    fclose(f);
    return 0;
}

static int write_text_file(const char *path, const char *text) {
    if (ensure_parent_dir(path) != 0) {
        return -1;
    }
    FILE *f = fopen(path, "wb");
    if (!f) {
        return -1;
    }
    size_t len = strlen(text);
    if (len > 0 && fwrite(text, 1, len, f) != len) {
        fclose(f);
        return -1;
    }
    fclose(f);
    return 0;
}

static char *trim_spaces(char *s) {
    while (*s && isspace((unsigned char)*s)) {
        s++;
    }
    char *e = s + strlen(s);
    while (e > s && isspace((unsigned char)e[-1])) {
        e--;
    }
    *e = '\0';
    return s;
}

static char *json_escape(const char *in) {
    struct strbuf out;
    strbuf_init(&out);
    if (strbuf_append(&out, "") != 0) {
        return NULL;
    }
    for (; *in; ++in) {
        unsigned char c = (unsigned char)*in;
        if (c == '"' || c == '\\') {
            char esc[3] = {'\\', (char)c, '\0'};
            if (strbuf_append(&out, esc) != 0) {
                strbuf_free(&out);
                return NULL;
            }
        } else if (c == '\n') {
            if (strbuf_append(&out, "\\n") != 0) {
                strbuf_free(&out);
                return NULL;
            }
        } else if (c == '\r') {
            if (strbuf_append(&out, "\\r") != 0) {
                strbuf_free(&out);
                return NULL;
            }
        } else if (c == '\t') {
            if (strbuf_append(&out, "\\t") != 0) {
                strbuf_free(&out);
                return NULL;
            }
        } else {
            char one[2] = {(char)c, '\0'};
            if (strbuf_append(&out, one) != 0) {
                strbuf_free(&out);
                return NULL;
            }
        }
    }
    return out.data;
}

static char *extract_json_string_field(const char *json, const char *field) {
    char pat[128];
    snprintf(pat, sizeof(pat), "\"%s\"", field);
    const char *p = strstr(json, pat);
    if (!p) {
        return NULL;
    }
    p += strlen(pat);
    while (*p && *p != ':') {
        p++;
    }
    if (*p != ':') {
        return NULL;
    }
    p++;
    while (*p && isspace((unsigned char)*p)) {
        p++;
    }
    if (*p != '"') {
        return NULL;
    }
    p++;
    struct strbuf out;
    strbuf_init(&out);
    while (*p && *p != '"') {
        if (*p == '\\' && p[1]) {
            p++;
            if (*p == 'n') {
                if (strbuf_append(&out, "\n") != 0) {
                    strbuf_free(&out);
                    return NULL;
                }
            } else if (*p == 'r') {
                if (strbuf_append(&out, "\r") != 0) {
                    strbuf_free(&out);
                    return NULL;
                }
            } else if (*p == 't') {
                if (strbuf_append(&out, "\t") != 0) {
                    strbuf_free(&out);
                    return NULL;
                }
            } else {
                char one[2] = {*p, '\0'};
                if (strbuf_append(&out, one) != 0) {
                    strbuf_free(&out);
                    return NULL;
                }
            }
        } else {
            char one[2] = {*p, '\0'};
            if (strbuf_append(&out, one) != 0) {
                strbuf_free(&out);
                return NULL;
            }
        }
        p++;
    }
    if (!out.data) {
        out.data = strdup("");
    }
    return out.data;
}

static char *build_url(const char *base_url, const char *endpoint) {
    if (!endpoint || !endpoint[0]) {
        return NULL;
    }
    if (strstr(endpoint, "http://") == endpoint || strstr(endpoint, "https://") == endpoint) {
        return strdup(endpoint);
    }
    struct strbuf b;
    strbuf_init(&b);
    strbuf_append(&b, base_url ? base_url : MELCLOUD_DEFAULT_BASE_URL);
    if (b.len > 0 && b.data[b.len - 1] == '/' && endpoint[0] == '/') {
        b.data[b.len - 1] = '\0';
        b.len--;
    } else if ((b.len == 0 || b.data[b.len - 1] != '/') && endpoint[0] != '/') {
        strbuf_append(&b, "/");
    }
    strbuf_append(&b, endpoint);
    return b.data;
}

static int http_request(const char *method,
                        const char *url,
                        const char *context_key,
                        const char *body,
                        long *status_code,
                        struct strbuf *resp) {
    CURL *curl = curl_easy_init();
    if (!curl) {
        return -1;
    }
    struct curl_slist *headers = NULL;
    headers = curl_slist_append(headers, "Accept: application/json, text/javascript, */*; q=0.01");
    headers = curl_slist_append(headers, "Accept-Language: en-US,en;q=0.5");
    headers = curl_slist_append(headers, "X-Requested-With: XMLHttpRequest");
    headers = curl_slist_append(headers, "Cookie: policyaccepted=true");
    headers = curl_slist_append(headers, "User-Agent: melcloud-cli/1.0");
    if (body) {
        headers = curl_slist_append(headers, "Content-Type: application/json");
    }
    if (context_key && context_key[0]) {
        char line[1024];
        snprintf(line, sizeof(line), "X-MitsContextKey: %s", context_key);
        headers = curl_slist_append(headers, line);
    }

    strbuf_init(resp);
    curl_easy_setopt(curl, CURLOPT_URL, url);
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, curl_write_cb);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, resp);
    curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, 45L);
    curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, 1L);
    curl_easy_setopt(curl, CURLOPT_SSL_VERIFYHOST, 2L);

    if (strcmp(method, "POST") == 0) {
        curl_easy_setopt(curl, CURLOPT_POST, 1L);
        curl_easy_setopt(curl, CURLOPT_POSTFIELDS, body ? body : "{}");
    }

    CURLcode rc = curl_easy_perform(curl);
    if (rc != CURLE_OK) {
        fprintf(stderr, "curl error: %s\n", curl_easy_strerror(rc));
        curl_slist_free_all(headers);
        curl_easy_cleanup(curl);
        strbuf_free(resp);
        return -1;
    }

    curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, status_code);
    curl_slist_free_all(headers);
    curl_easy_cleanup(curl);
    return 0;
}

static const char *resolve_context(int argc, char **argv) {
    const char *ctx = arg_value(argc, argv, "--context");
    if (ctx && ctx[0]) {
        return ctx;
    }
    const char *session = arg_value(argc, argv, "--session");
    if (!session) {
        session = MELCLOUD_DEFAULT_SESSION_FILE;
    }
    static char loaded[1024];
    FILE *f = fopen(session, "r");
    if (!f) {
        return NULL;
    }
    if (!fgets(loaded, sizeof(loaded), f)) {
        fclose(f);
        return NULL;
    }
    fclose(f);
    char *t = trim_spaces(loaded);
    if (!t[0]) {
        return NULL;
    }
    memmove(loaded, t, strlen(t) + 1);
    return loaded;
}

static int print_http_json(const char *method,
                           const char *base_url,
                           const char *endpoint,
                           const char *ctx,
                           const char *body) {
    char *url = build_url(base_url, endpoint);
    if (!url) {
        fprintf(stderr, "Invalid endpoint\n");
        return 2;
    }
    struct strbuf resp;
    long code = 0;
    int rc = http_request(method, url, ctx, body, &code, &resp);
    free(url);
    if (rc != 0) {
        return 2;
    }
    if (resp.data && resp.data[0]) {
        puts(resp.data);
    } else {
        puts("{}");
    }
    strbuf_free(&resp);
    return (code >= 200 && code < 300) ? 0 : 3;
}

static int cmd_login_common(int argc, char **argv, const char *login_endpoint) {
    const char *email = arg_value(argc, argv, "--email");
    const char *password = arg_value(argc, argv, "--password");
    const char *base_url = arg_value(argc, argv, "--base-url");
    const char *app_version = arg_value(argc, argv, "--app-version");
    const char *session = arg_value(argc, argv, "--session");
    if (!base_url) {
        base_url = MELCLOUD_DEFAULT_BASE_URL;
    }
    if (!app_version) {
        app_version = MELCLOUD_DEFAULT_APP_VERSION;
    }
    if (!session) {
        session = MELCLOUD_DEFAULT_SESSION_FILE;
    }
    if (!email || !password) {
        fprintf(stderr, "login requires --email and --password\n");
        return 2;
    }

    char *email_e = json_escape(email);
    char *pass_e = json_escape(password);
    char *app_e = json_escape(app_version);
    if (!email_e || !pass_e || !app_e) {
        free(email_e);
        free(pass_e);
        free(app_e);
        return 2;
    }

    struct strbuf body;
    strbuf_init(&body);
    strbuf_append(&body, "{");
    strbuf_append(&body, "\"Email\":\"");
    strbuf_append(&body, email_e);
    strbuf_append(&body, "\",");
    strbuf_append(&body, "\"Password\":\"");
    strbuf_append(&body, pass_e);
    strbuf_append(&body, "\",");
    strbuf_append(&body, "\"Language\":0,");
    strbuf_append(&body, "\"AppVersion\":\"");
    strbuf_append(&body, app_e);
    strbuf_append(&body, "\",");
    strbuf_append(&body, "\"Persist\":true,");
    strbuf_append(&body, "\"CaptchaResponse\":null,");
    strbuf_append(&body, "\"CaptchaChallenge\":\"\"");
    strbuf_append(&body, "}");

    char *url = build_url(base_url, login_endpoint);
    struct strbuf resp;
    long code = 0;
    int rc = http_request("POST", url, NULL, body.data, &code, &resp);

    free(url);
    free(email_e);
    free(pass_e);
    free(app_e);
    strbuf_free(&body);

    if (rc != 0) {
        return 2;
    }

    if (resp.data) {
        puts(resp.data);
    }

    char *key = extract_json_string_field(resp.data ? resp.data : "", "ContextKey");
    if (key && key[0]) {
        if (write_text_file(session, key) != 0) {
            fprintf(stderr, "Warning: failed to save session key to %s\n", session);
        }
        fprintf(stderr, "Saved context key to %s\n", session);
        free(key);
    } else {
        fprintf(stderr, "ContextKey not found in response\n");
        strbuf_free(&resp);
        free(key);
        return (code >= 200 && code < 300) ? 4 : 3;
    }

    strbuf_free(&resp);
    return (code >= 200 && code < 300) ? 0 : 3;
}

static int cmd_login(int argc, char **argv) {
    return cmd_login_common(argc, argv, "/Login/ClientLogin");
}

static int cmd_login2(int argc, char **argv) {
    return cmd_login_common(argc, argv, "/Login/ClientLogin2");
}

static char *load_json_arg(int argc, char **argv) {
    const char *json_txt = arg_value(argc, argv, "--json-text");
    if (json_txt) {
        return strdup(json_txt);
    }
    const char *json_file = arg_value(argc, argv, "--json");
    if (!json_file) {
        return NULL;
    }
    struct strbuf data;
    if (read_text_file(json_file, &data) != 0) {
        return NULL;
    }
    return data.data;
}

static int cmd_raw_get(int argc, char **argv) {
    const char *base_url = arg_value(argc, argv, "--base-url");
    const char *endpoint = arg_value(argc, argv, "--endpoint");
    const char *ctx = resolve_context(argc, argv);
    if (!base_url) {
        base_url = MELCLOUD_DEFAULT_BASE_URL;
    }
    if (!ctx || !endpoint) {
        fprintf(stderr, "raw-get requires --context/--session and --endpoint\n");
        return 2;
    }
    return print_http_json("GET", base_url, endpoint, ctx, NULL);
}

static int cmd_raw_post(int argc, char **argv) {
    const char *base_url = arg_value(argc, argv, "--base-url");
    const char *endpoint = arg_value(argc, argv, "--endpoint");
    const char *ctx = resolve_context(argc, argv);
    if (!base_url) {
        base_url = MELCLOUD_DEFAULT_BASE_URL;
    }
    if (!ctx || !endpoint) {
        fprintf(stderr, "raw-post requires --context/--session and --endpoint\n");
        return 2;
    }
    char *json = load_json_arg(argc, argv);
    if (!json) {
        fprintf(stderr, "raw-post requires --json <file> or --json-text <json>\n");
        return 2;
    }
    int rc = print_http_json("POST", base_url, endpoint, ctx, json);
    free(json);
    return rc;
}

static int cmd_list_devices(int argc, char **argv) {
    const char *base_url = arg_value(argc, argv, "--base-url");
    const char *ctx = resolve_context(argc, argv);
    if (!base_url) {
        base_url = MELCLOUD_DEFAULT_BASE_URL;
    }
    if (!ctx) {
        fprintf(stderr, "list-devices requires --context/--session\n");
        return 2;
    }
    return print_http_json("GET", base_url, "/User/ListDevices", ctx, NULL);
}

static int cmd_get_user_details(int argc, char **argv) {
    const char *base_url = arg_value(argc, argv, "--base-url");
    const char *ctx = resolve_context(argc, argv);
    if (!base_url) {
        base_url = MELCLOUD_DEFAULT_BASE_URL;
    }
    if (!ctx) {
        fprintf(stderr, "get-user-details requires --context/--session\n");
        return 2;
    }
    return print_http_json("GET", base_url, "/User/GetUserDetails", ctx, NULL);
}

static int cmd_get_device(int argc, char **argv) {
    const char *base_url = arg_value(argc, argv, "--base-url");
    const char *ctx = resolve_context(argc, argv);
    const char *id = arg_value(argc, argv, "--id");
    const char *building = arg_value(argc, argv, "--building");
    if (!base_url) {
        base_url = MELCLOUD_DEFAULT_BASE_URL;
    }
    if (!ctx || !id || !building) {
        fprintf(stderr, "get-device requires --context/--session --id --building\n");
        return 2;
    }
    char endpoint[256];
    snprintf(endpoint, sizeof(endpoint), "/Device/Get?id=%s&buildingID=%s", id, building);
    return print_http_json("GET", base_url, endpoint, ctx, NULL);
}

static int cmd_list_device_units(int argc, char **argv) {
    const char *base_url = arg_value(argc, argv, "--base-url");
    const char *ctx = resolve_context(argc, argv);
    const char *id = arg_value(argc, argv, "--id");
    if (!base_url) {
        base_url = MELCLOUD_DEFAULT_BASE_URL;
    }
    if (!ctx || !id) {
        fprintf(stderr, "list-device-units requires --context/--session --id\n");
        return 2;
    }

    struct strbuf body;
    strbuf_init(&body);
    strbuf_append(&body, "{");
    strbuf_append(&body, "\"deviceId\":");
    strbuf_append(&body, id);
    strbuf_append(&body, ",\"DeviceID\":");
    strbuf_append(&body, id);
    strbuf_append(&body, "}");

    int rc = print_http_json("POST", base_url, "/Device/ListDeviceUnits", ctx, body.data);
    strbuf_free(&body);
    return rc;
}

static char *merge_device_payload(const char *id, const char *building, const char *json_obj) {
    if (!json_obj) {
        return NULL;
    }
    char *tmp = strdup(json_obj);
    if (!tmp) {
        return NULL;
    }
    char *t = trim_spaces(tmp);
    if (!t[0]) {
        free(tmp);
        return NULL;
    }

    const char *content_start = t;
    size_t content_len = strlen(t);
    if (t[0] == '{') {
        content_start = t + 1;
        content_len = strlen(content_start);
        while (content_len > 0 && isspace((unsigned char)content_start[content_len - 1])) {
            content_len--;
        }
        if (content_len > 0 && content_start[content_len - 1] == '}') {
            content_len--;
        }
        while (content_len > 0 && isspace((unsigned char)content_start[content_len - 1])) {
            content_len--;
        }
    }

    struct strbuf out;
    strbuf_init(&out);
    strbuf_append(&out, "{");
    strbuf_append(&out, "\"DeviceID\":");
    strbuf_append(&out, id);
    strbuf_append(&out, ",\"BuildingID\":");
    strbuf_append(&out, building);

    if (content_len > 0) {
        strbuf_append(&out, ",");
        strbuf_append_n(&out, content_start, content_len);
    }

    strbuf_append(&out, "}");
    free(tmp);
    return out.data;
}

static int cmd_set_device_common(int argc, char **argv, const char *endpoint) {
    const char *base_url = arg_value(argc, argv, "--base-url");
    const char *ctx = resolve_context(argc, argv);
    const char *id = arg_value(argc, argv, "--id");
    const char *building = arg_value(argc, argv, "--building");
    if (!base_url) {
        base_url = MELCLOUD_DEFAULT_BASE_URL;
    }
    if (!ctx || !id || !building) {
        fprintf(stderr, "set command requires --context/--session --id --building\n");
        return 2;
    }

    char *tpl_json = load_json_arg(argc, argv);
    if (!tpl_json) {
        fprintf(stderr, "set command requires --json <file> or --json-text <json>\n");
        return 2;
    }
    char *payload = merge_device_payload(id, building, tpl_json);
    free(tpl_json);
    if (!payload) {
        fprintf(stderr, "Invalid JSON payload\n");
        return 2;
    }
    int rc = print_http_json("POST", base_url, endpoint, ctx, payload);
    free(payload);
    return rc;
}

static int cmd_energy_report(int argc, char **argv) {
    const char *base_url = arg_value(argc, argv, "--base-url");
    const char *ctx = resolve_context(argc, argv);
    const char *id = arg_value(argc, argv, "--id");
    const char *from = arg_value(argc, argv, "--from");
    const char *to = arg_value(argc, argv, "--to");
    const char *currency = arg_value(argc, argv, "--currency");

    if (!base_url) {
        base_url = MELCLOUD_DEFAULT_BASE_URL;
    }
    if (!ctx || !id || !from || !to) {
        fprintf(stderr, "energy-report requires --context/--session --id --from --to\n");
        return 2;
    }
    if (!currency) {
        currency = "false";
    }

    struct strbuf body;
    strbuf_init(&body);
    strbuf_append(&body, "{");
    strbuf_append(&body, "\"DeviceID\":");
    strbuf_append(&body, id);
    strbuf_append(&body, ",\"UseCurrency\":");
    strbuf_append(&body, currency);
    strbuf_append(&body, ",\"FromDate\":\"");
    strbuf_append(&body, from);
    strbuf_append(&body, "\",");
    strbuf_append(&body, "\"ToDate\":\"");
    strbuf_append(&body, to);
    strbuf_append(&body, "\"}");

    int rc = print_http_json("POST", base_url, "/EnergyCost/Report", ctx, body.data);
    strbuf_free(&body);
    return rc;
}

static int cmd_update_application_options(int argc, char **argv) {
    const char *base_url = arg_value(argc, argv, "--base-url");
    const char *ctx = resolve_context(argc, argv);
    if (!base_url) {
        base_url = MELCLOUD_DEFAULT_BASE_URL;
    }
    if (!ctx) {
        fprintf(stderr, "update-application-options requires --context/--session\n");
        return 2;
    }

    char *json = load_json_arg(argc, argv);
    if (!json) {
        fprintf(stderr, "update-application-options requires --json <file> or --json-text <json>\n");
        return 2;
    }
    int rc = print_http_json("POST", base_url, "/User/UpdateApplicationOptions", ctx, json);
    free(json);
    return rc;
}

static int cmd_set_options(int argc, char **argv) {
    const char *base_url = arg_value(argc, argv, "--base-url");
    const char *ctx = resolve_context(argc, argv);
    const char *id = arg_value(argc, argv, "--id");
    const char *building = arg_value(argc, argv, "--building");
    if (!base_url) {
        base_url = MELCLOUD_DEFAULT_BASE_URL;
    }
    if (!ctx || !id || !building) {
        fprintf(stderr, "set-options requires --context/--session --id --building\n");
        return 2;
    }

    char *json = load_json_arg(argc, argv);
    if (!json) {
        fprintf(stderr, "set-options requires --json <file> or --json-text <json>\n");
        return 2;
    }
    char *payload = merge_device_payload(id, building, json);
    free(json);
    if (!payload) {
        fprintf(stderr, "Invalid JSON payload\n");
        return 2;
    }

    int rc = print_http_json("POST", base_url, "/Device/SetOptions", ctx, payload);
    free(payload);
    return rc;
}

static int valid_template_name(const char *name) {
    if (!name || !name[0]) {
        return 0;
    }
    for (; *name; ++name) {
        char c = *name;
        if (!(isalnum((unsigned char)c) || c == '_' || c == '-' || c == '.')) {
            return 0;
        }
    }
    return 1;
}

static char *template_path(const char *dir, const char *name) {
    struct strbuf p;
    strbuf_init(&p);
    strbuf_append(&p, dir ? dir : MELCLOUD_DEFAULT_TEMPLATE_DIR);
    if (p.len == 0 || p.data[p.len - 1] != '/') {
        strbuf_append(&p, "/");
    }
    strbuf_append(&p, name);
    strbuf_append(&p, ".json");
    return p.data;
}

static int cmd_template_save(int argc, char **argv) {
    const char *name = arg_value(argc, argv, "--name");
    const char *dir = arg_value(argc, argv, "--template-dir");
    if (!dir) {
        dir = MELCLOUD_DEFAULT_TEMPLATE_DIR;
    }
    if (!valid_template_name(name)) {
        fprintf(stderr, "template-save requires a safe --name\n");
        return 2;
    }
    if (ensure_dir(dir) != 0) {
        fprintf(stderr, "cannot create template dir: %s\n", dir);
        return 2;
    }
    char *json = load_json_arg(argc, argv);
    if (!json) {
        fprintf(stderr, "template-save requires --json <file> or --json-text <json>\n");
        return 2;
    }
    char *path = template_path(dir, name);
    int rc = write_text_file(path, json);
    free(json);
    if (rc != 0) {
        fprintf(stderr, "failed to write %s\n", path);
        free(path);
        return 2;
    }
    printf("{\"success\":true,\"template\":\"%s\",\"path\":\"%s\"}\n", name, path);
    free(path);
    return 0;
}

static int cmd_template_show(int argc, char **argv) {
    const char *name = arg_value(argc, argv, "--name");
    const char *dir = arg_value(argc, argv, "--template-dir");
    if (!dir) {
        dir = MELCLOUD_DEFAULT_TEMPLATE_DIR;
    }
    if (!valid_template_name(name)) {
        fprintf(stderr, "template-show requires a safe --name\n");
        return 2;
    }
    char *path = template_path(dir, name);
    struct strbuf data;
    int rc = read_text_file(path, &data);
    free(path);
    if (rc != 0) {
        fprintf(stderr, "template not found\n");
        return 2;
    }
    puts(data.data ? data.data : "{}");
    strbuf_free(&data);
    return 0;
}

static int cmd_template_delete(int argc, char **argv) {
    const char *name = arg_value(argc, argv, "--name");
    const char *dir = arg_value(argc, argv, "--template-dir");
    if (!dir) {
        dir = MELCLOUD_DEFAULT_TEMPLATE_DIR;
    }
    if (!valid_template_name(name)) {
        fprintf(stderr, "template-delete requires a safe --name\n");
        return 2;
    }
    char *path = template_path(dir, name);
    if (unlink(path) != 0) {
        fprintf(stderr, "failed to remove %s\n", path);
        free(path);
        return 2;
    }
    printf("{\"success\":true,\"deleted\":\"%s\"}\n", name);
    free(path);
    return 0;
}

static int cmd_template_list(int argc, char **argv) {
    const char *dir = arg_value(argc, argv, "--template-dir");
    if (!dir) {
        dir = MELCLOUD_DEFAULT_TEMPLATE_DIR;
    }
    DIR *d = opendir(dir);
    if (!d) {
        puts("[]");
        return 0;
    }
    puts("[");
    int first = 1;
    struct dirent *ent;
    while ((ent = readdir(d)) != NULL) {
        size_t n = strlen(ent->d_name);
        if (n < 6) {
            continue;
        }
        if (strcmp(ent->d_name + n - 5, ".json") != 0) {
            continue;
        }
        char name[512];
        if (n - 5 >= sizeof(name)) {
            continue;
        }
        memcpy(name, ent->d_name, n - 5);
        name[n - 5] = '\0';
        if (!first) {
            puts(",");
        }
        first = 0;
        printf("  {\"name\":\"%s\"}", name);
    }
    puts("\n]");
    closedir(d);
    return 0;
}

static int cmd_template_apply(int argc, char **argv) {
    const char *type = arg_value(argc, argv, "--type");
    const char *name = arg_value(argc, argv, "--name");
    const char *dir = arg_value(argc, argv, "--template-dir");
    const char *id = arg_value(argc, argv, "--id");
    const char *building = arg_value(argc, argv, "--building");
    if (!dir) {
        dir = MELCLOUD_DEFAULT_TEMPLATE_DIR;
    }
    if (!valid_template_name(name) || !type || !id || !building) {
        fprintf(stderr, "template-apply requires --type --name --id --building\n");
        return 2;
    }
    char *path = template_path(dir, name);
    struct strbuf data;
    if (read_text_file(path, &data) != 0) {
        fprintf(stderr, "template not found\n");
        free(path);
        return 2;
    }
    free(path);

    char *payload = merge_device_payload(id, building, data.data ? data.data : "{}");
    strbuf_free(&data);
    if (!payload) {
        fprintf(stderr, "cannot build payload\n");
        return 2;
    }

    const char *endpoint = NULL;
    if (strcmp(type, "ata") == 0) {
        endpoint = "/Device/SetAta";
    } else if (strcmp(type, "atw") == 0) {
        endpoint = "/Device/SetAtw";
    } else if (strcmp(type, "erv") == 0) {
        endpoint = "/Device/SetErv";
    } else {
        fprintf(stderr, "type must be ata|atw|erv\n");
        free(payload);
        return 2;
    }

    const char *base_url = arg_value(argc, argv, "--base-url");
    const char *ctx = resolve_context(argc, argv);
    if (!base_url) {
        base_url = MELCLOUD_DEFAULT_BASE_URL;
    }
    if (!ctx) {
        fprintf(stderr, "template-apply requires --context/--session\n");
        free(payload);
        return 2;
    }

    int rc = print_http_json("POST", base_url, endpoint, ctx, payload);
    free(payload);
    return rc;
}

static void print_usage(const char *prog) {
    fprintf(stderr,
            "Usage: %s <command> [options]\n"
            "\n"
            "Auth/session:\n"
            "  login --email E --password P [--base-url URL] [--app-version V] [--session FILE]\n"
            "  login2 --email E --password P [--base-url URL] [--app-version V] [--session FILE]\n"
            "\n"
            "Read operations:\n"
            "  list-devices [--context KEY|--session FILE] [--base-url URL]\n"
            "  get-user-details [--context KEY|--session FILE] [--base-url URL]\n"
            "  get-device --id ID --building BID [--context KEY|--session FILE] [--base-url URL]\n"
            "  list-device-units --id ID [--context KEY|--session FILE] [--base-url URL]\n"
            "  energy-report --id ID --from ISO --to ISO [--currency true|false] [--context KEY|--session FILE]\n"
            "\n"
            "Write operations:\n"
            "  set-ata --id ID --building BID --json payload.json [--context KEY|--session FILE]\n"
            "  set-atw --id ID --building BID --json payload.json [--context KEY|--session FILE]\n"
            "  set-erv --id ID --building BID --json payload.json [--context KEY|--session FILE]\n"
            "  set-options --id ID --building BID --json payload.json [--context KEY|--session FILE]\n"
            "  update-application-options --json payload.json [--context KEY|--session FILE]\n"
            "\n"
            "Raw API passthrough:\n"
            "  raw-get --endpoint /User/ListDevices [--context KEY|--session FILE] [--base-url URL]\n"
            "  raw-post --endpoint /Device/SetAta --json payload.json [--context KEY|--session FILE] [--base-url URL]\n"
            "  api-get --endpoint /PATH [--context KEY|--session FILE] [--base-url URL]\n"
            "  api-post --endpoint /PATH --json payload.json [--context KEY|--session FILE] [--base-url URL]\n"
            "\n"
            "Template management:\n"
            "  template-save --name N --json payload.json [--template-dir DIR]\n"
            "  template-show --name N [--template-dir DIR]\n"
            "  template-list [--template-dir DIR]\n"
            "  template-delete --name N [--template-dir DIR]\n"
            "  template-apply --type ata|atw|erv --name N --id ID --building BID [--context KEY|--session FILE] [--template-dir DIR]\n",
            prog);
}

int main(int argc, char **argv) {
    if (argc < 2) {
        print_usage(argv[0]);
        return 2;
    }

    curl_global_init(CURL_GLOBAL_DEFAULT);

    int rc = 2;
    const char *cmd = argv[1];

    if (strcmp(cmd, "login") == 0) {
        rc = cmd_login(argc, argv);
    } else if (strcmp(cmd, "login2") == 0) {
        rc = cmd_login2(argc, argv);
    } else if (strcmp(cmd, "list-devices") == 0) {
        rc = cmd_list_devices(argc, argv);
    } else if (strcmp(cmd, "get-user-details") == 0) {
        rc = cmd_get_user_details(argc, argv);
    } else if (strcmp(cmd, "get-device") == 0) {
        rc = cmd_get_device(argc, argv);
    } else if (strcmp(cmd, "list-device-units") == 0) {
        rc = cmd_list_device_units(argc, argv);
    } else if (strcmp(cmd, "set-ata") == 0) {
        rc = cmd_set_device_common(argc, argv, "/Device/SetAta");
    } else if (strcmp(cmd, "set-atw") == 0) {
        rc = cmd_set_device_common(argc, argv, "/Device/SetAtw");
    } else if (strcmp(cmd, "set-erv") == 0) {
        rc = cmd_set_device_common(argc, argv, "/Device/SetErv");
    } else if (strcmp(cmd, "set-options") == 0) {
        rc = cmd_set_options(argc, argv);
    } else if (strcmp(cmd, "update-application-options") == 0) {
        rc = cmd_update_application_options(argc, argv);
    } else if (strcmp(cmd, "energy-report") == 0) {
        rc = cmd_energy_report(argc, argv);
    } else if (strcmp(cmd, "raw-get") == 0) {
        rc = cmd_raw_get(argc, argv);
    } else if (strcmp(cmd, "raw-post") == 0) {
        rc = cmd_raw_post(argc, argv);
    } else if (strcmp(cmd, "api-get") == 0) {
        rc = cmd_raw_get(argc, argv);
    } else if (strcmp(cmd, "api-post") == 0) {
        rc = cmd_raw_post(argc, argv);
    } else if (strcmp(cmd, "template-save") == 0) {
        rc = cmd_template_save(argc, argv);
    } else if (strcmp(cmd, "template-show") == 0) {
        rc = cmd_template_show(argc, argv);
    } else if (strcmp(cmd, "template-list") == 0) {
        rc = cmd_template_list(argc, argv);
    } else if (strcmp(cmd, "template-delete") == 0) {
        rc = cmd_template_delete(argc, argv);
    } else if (strcmp(cmd, "template-apply") == 0) {
        rc = cmd_template_apply(argc, argv);
    } else if (strcmp(cmd, "--help") == 0 || strcmp(cmd, "-h") == 0 || strcmp(cmd, "help") == 0) {
        print_usage(argv[0]);
        rc = 0;
    } else {
        fprintf(stderr, "Unknown command: %s\n\n", cmd);
        print_usage(argv[0]);
        rc = 2;
    }

    curl_global_cleanup();
    return rc;
}
