/*
 * freetz_proxy.c - CGI HTTPS gateway / reverse proxy for FritzBox
 *
 * Purpose:
 *   Provides an HTTPS entry-point so that PWA installation is possible,
 *   and proxies simple Freetz pages.  Complex apps (ruTorrent, ttyd/WS…)
 *   are exposed as direct HTTP links instead of being proxied.
 *
 * Config file: /mod/etc/conf/freetz-proxy.cfg
 *   Format:  name=port[:path[:direct]]
 *     name   - service identifier
 *     port   - upstream TCP port on 127.0.0.1
 *     path   - default upstream path (default: /)
 *     direct - literal word "direct": show as a plain HTTP link on the
 *              index page instead of routing through the proxy
 *   Lines starting with # are comments.
 *   Example:
 *     freetz=81
 *     rutorrent=81:/rutorrent/:direct
 *     ttyd=7681::direct
 *
 * The "freetz" service is auto-added from MOD_HTTPD_PORT in
 * /mod/etc/conf/mod.cfg when it is absent from the config file.
 *
 * Proxied URL scheme:
 *   https://fritz.box/cgi-bin/freetz_proxy             -> index page
 *   https://fritz.box/cgi-bin/freetz_proxy?service=X   -> proxy to port
 *
 * Compile (cross):
 *   $(CC) $(CFLAGS) -o freetz_proxy freetz_proxy.c
 */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <ctype.h>
#include <errno.h>
#include <time.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <fnmatch.h>

#define FREETZ_HOST          "127.0.0.1"
#define DEFAULT_FREETZ_PORT   81
#define BUF_SIZE              8192
#define MAX_SERVICES          32
#define MAX_NAME_LEN          64

/* ------------------------------------------------------------------
 * Optional debug trace.
 * Enable:  set @trace_file=/tmp/freetz_proxy.log in freetz-proxy.cfg
 * Disable: set @trace_file= (empty) in freetz-proxy.cfg
 * Log:     tail -f /tmp/freetz_proxy.log
 * ------------------------------------------------------------------ */
static FILE *g_dbg      = NULL;
static char  g_trace_file[256] = "";  /* @trace_file=path: trace to this file if non-empty */
static void dbg_open(void) {
    if (!g_trace_file[0]) return;  /* no trace_file configured → silent */
    g_dbg = fopen(g_trace_file, "a");
}
#define DBG(...) do { if (g_dbg) { \
    fprintf(g_dbg, "[%ld] ", (long)time(NULL)); \
    fprintf(g_dbg, __VA_ARGS__); \
    fputc('\n', g_dbg); fflush(g_dbg); } } while(0)

/* Body buffers for HTML/CSS rewriting (static = allocated once, CGI is
 * single-threaded and short-lived so no concern about re-entrancy) */
#define BODY_IN_MAX   (256 * 1024)
#define BODY_OUT_MAX  (BODY_IN_MAX + 128 * 1024)
static char g_body_in [BODY_IN_MAX  + 1];
static char g_body_out[BODY_OUT_MAX + 1];

/* Method-tunnel buffer: when AVM websrv rejects POST from internet,
 * the client encodes the POST body in _body= and signals _method=POST.
 * The proxy decodes it here and feeds it to the upstream instead of stdin.
 * Note: AVM websrv limits QUERY_STRING to ~8 KB; the URL-encoded body can
 * be up to 3× the decoded size, so 4 KB decoded fits comfortably within
 * that limit and covers all typical Freetz config form submissions. */
#define TUNNEL_BODY_MAX (4 * 1024)
static char g_tunnel_body[TUNNEL_BODY_MAX + 1];
static int  g_tunnel_body_len = 0;
static char g_tunnel_clen_str[32];   /* Content-Length string for do_proxy */
static char g_tunnel_ctype_str[128]; /* Content-Type  string for do_proxy */

/* ------------------------------------------------------------------
 * Service registry
 * ------------------------------------------------------------------ */
typedef struct {
    char name[MAX_NAME_LEN];
    int  port;
    char path[256]; /* default upstream path, e.g. "/" or "/rutorrent/" */
    int  direct;    /* 1 = index links directly to http://host:port/path */
} Service;
static Service services[MAX_SERVICES];
static int     n_services = 0;

/* ------------------------------------------------------------------
 * Security options loaded from @key=value directives in the config.
 * Defaults: no_internet_cookie=1 (strip Max-Age when from internet).
 * ------------------------------------------------------------------ */
static int g_no_cookie          = 0;  /* @no_cookie=yes: session-only cookies always */
static int g_no_internet_cookie = 1;  /* @no_internet_cookie=yes (default): session-only when from internet */
static int g_block_internet     = 0;  /* @block_internet=yes: return 403 from internet */
static int g_disabled           = 0;  /* @disabled=yes: return notice page for all requests */
static int g_is_internet        = 0;  /* set in main() based on SERVER_NAME */

/* Configurable list of hostname substrings that indicate internet access.
 * Default: ".myfritz.net". Override via @internet_domains= in config. */
#define MAX_INTERNET_PATTERNS  16
#define MAX_PATTERN_LEN        128
static char g_internet_patterns[MAX_INTERNET_PATTERNS][MAX_PATTERN_LEN];
static int  g_n_internet_patterns = 0;

static void init_internet_patterns(void) {
    strncpy(g_internet_patterns[0], ".myfritz.net", MAX_PATTERN_LEN - 1);
    g_internet_patterns[0][MAX_PATTERN_LEN - 1] = '\0';
    g_n_internet_patterns = 1;
}

static int is_internet_host(const char *server_name) {
    if (!server_name || !*server_name) return 0;
    for (int i = 0; i < g_n_internet_patterns; i++)
        if (strstr(server_name, g_internet_patterns[i]) != NULL)
            return 1;
    return 0;
}

/* ------------------------------------------------------------------
 * Buffered socket reader
 * ------------------------------------------------------------------ */
typedef struct {
    int  fd;
    char buf[BUF_SIZE];
    int  pos;
    int  len;
    int  eof;
} BufReader;

static void br_init(BufReader *br, int fd) {
    br->fd  = fd;
    br->pos = 0;
    br->len = 0;
    br->eof = 0;
}

/* Returns 1 on success, 0 on EOF, -1 on error */
static int br_getc(BufReader *br, char *out) {
    if (br->eof) return 0;
    if (br->pos >= br->len) {
        br->len = (int)read(br->fd, br->buf, BUF_SIZE);
        if (br->len <= 0) {
            br->eof = 1;
            return (br->len == 0) ? 0 : -1;
        }
        br->pos = 0;
    }
    *out = br->buf[br->pos++];
    return 1;
}

/* Read one line (stripping \r\n). Returns chars in line (0 = empty line, -1 = EOF/error) */
static int br_readline(BufReader *br, char *line, int maxlen) {
    int n = 0;
    char c;
    while (1) {
        int r = br_getc(br, &c);
        if (r <= 0) return (n > 0) ? n : -1;
        if (c == '\r') continue;
        if (c == '\n') break;
        if (n < maxlen - 1)
            line[n++] = c;
    }
    line[n] = '\0';
    return n;
}

/* Write all bytes or die */
static int write_all(int fd, const char *buf, int len) {
    int sent = 0;
    while (sent < len) {
        int w = (int)write(fd, buf + sent, (size_t)(len - sent));
        if (w <= 0) return -1;
        sent += w;
    }
    return 0;
}

static int write_str(int fd, const char *s) {
    return write_all(fd, s, (int)strlen(s));
}

/* ------------------------------------------------------------------
 * Read Freetz-EVO HTTP port from /mod/etc/conf/mod.cfg
 * ------------------------------------------------------------------ */
static int get_freetz_port(void) {
    FILE *f = fopen("/mod/etc/conf/mod.cfg", "r");
    if (!f)
        return DEFAULT_FREETZ_PORT;

    char line[256];
    int port = DEFAULT_FREETZ_PORT;
    while (fgets(line, (int)sizeof(line), f)) {
        char *nl = strchr(line, '\n');
        if (nl) *nl = '\0';
        if (strncmp(line, "MOD_HTTPD_PORT=", 15) == 0) {
            char *val = line + 15;
            if (*val == '\'' || *val == '"') val++;
            port = atoi(val);
            if (port <= 0) port = DEFAULT_FREETZ_PORT;
            break;
        }
    }
    fclose(f);
    return port;
}

/* ------------------------------------------------------------------
 * Strip Max-Age=... and Expires=... from a Set-Cookie response header,
 * converting it to a session-only cookie.  SameSite, HttpOnly, Path,
 * Domain and other attributes are preserved unchanged.
 * ------------------------------------------------------------------ */
static void strip_cookie_maxage(const char *in, char *out, int outsz) {
    const char *p = in;
    int written = 0;
    while (*p && written < outsz - 1) {
        if (*p == ';') {
            const char *look = p + 1;
            while (*look == ' ' || *look == '\t') look++;
            if (strncasecmp(look, "max-age=", 8) == 0 ||
                strncasecmp(look, "expires=", 8) == 0) {
                /* skip the whole attribute (up to next ';' or end) */
                while (*look && *look != ';') look++;
                p = look;
                continue;
            }
        }
        out[written++] = *p++;
    }
    out[written] = '\0';
}

/* ------------------------------------------------------------------
 * Load service config into services[].
 * Tries /tmp/flash/mod/freetz-proxy.cfg first (NAND flash, editable
 * via the Freetz web UI), then falls back to /mod/etc/conf/freetz-proxy.cfg.
 * ------------------------------------------------------------------ */
static void load_config(void) {
    FILE *f = fopen("/tmp/flash/mod/freetz-proxy.cfg", "r");
    if (!f)
        f = fopen("/mod/etc/conf/freetz-proxy.cfg", "r");
    if (!f)
        return;

    char line[256];
    while (fgets(line, (int)sizeof(line), f) && n_services < MAX_SERVICES) {
        /* strip trailing newline / CR */
        char *nl = strchr(line, '\n'); if (nl) *nl = '\0';
        nl = strchr(line, '\r'); if (nl) *nl = '\0';

        /* skip blanks and comments */
        char *p = line;
        while (*p == ' ' || *p == '\t') p++;
        if (*p == '\0' || *p == '#') continue;

        char *eq = strchr(p, '=');
        if (!eq) continue;

        /* Handle security/option directives: @key=value
         * These configure proxy behaviour but are not service entries. */
        if (*p == '@') {
            const char *key = p + 1;
            int klen = (int)(eq - key);
            const char *val = eq + 1;
            int bval = (strcmp(val, "yes") == 0) ? 1 : 0;
            if      (klen == 9  && strncmp(key, "no_cookie",          9)  == 0)
                g_no_cookie = bval;
            else if (klen == 18 && strncmp(key, "no_internet_cookie", 18) == 0)
                g_no_internet_cookie = bval;
            else if (klen == 14 && strncmp(key, "block_internet",    14) == 0)
                g_block_internet = bval;
            else if (klen == 8  && strncmp(key, "disabled",           8) == 0)
                g_disabled = bval;
            else if (klen == 10 && strncmp(key, "trace_file",        10) == 0)
                strncpy(g_trace_file, val, sizeof(g_trace_file) - 1);
            else if (klen == 16 && strncmp(key, "internet_domains", 16) == 0) {
                /* comma-separated list of substrings that indicate internet access */
                g_n_internet_patterns = 0;
                char _dtmp[256];
                strncpy(_dtmp, val, sizeof(_dtmp) - 1);
                _dtmp[sizeof(_dtmp) - 1] = '\0';
                char *_tok = strtok(_dtmp, ",");
                while (_tok && g_n_internet_patterns < MAX_INTERNET_PATTERNS) {
                    while (*_tok == ' ' || *_tok == '\t') _tok++;
                    char *_end = _tok + strlen(_tok);
                    while (_end > _tok && (*(_end-1) == ' ' || *(_end-1) == '\t')) _end--;
                    int _plen = (int)(_end - _tok);
                    if (_plen > 0 && _plen < MAX_PATTERN_LEN) {
                        memcpy(g_internet_patterns[g_n_internet_patterns], _tok, (size_t)_plen);
                        g_internet_patterns[g_n_internet_patterns][_plen] = '\0';
                        g_n_internet_patterns++;
                    }
                    _tok = strtok(NULL, ",");
                }
            }
            continue; /* not a service entry */
        }

        int nlen = (int)(eq - p);
        if (nlen <= 0 || nlen >= MAX_NAME_LEN) continue;

        /* value may be: port   or   port:path   or   port:path:direct */
        char *colon1 = strchr(eq + 1, ':');
        int port;
        if (colon1) {
            *colon1 = '\0';
            port = atoi(eq + 1);
            *colon1 = ':';
        } else {
            port = atoi(eq + 1);
        }
        if (port < 0 || port > 65535) continue;
        /* port == 0 is a shorthand for "use the Freetz HTTP port" */
        if (port == 0) port = get_freetz_port();

        memcpy(services[n_services].name, p, (size_t)nlen);
        services[n_services].name[nlen] = '\0';
        services[n_services].port = port;

        /* defaults */
        strncpy(services[n_services].path, "/", sizeof(services[n_services].path) - 1);
        services[n_services].path[sizeof(services[n_services].path) - 1] = '\0';
        services[n_services].direct = 0;

        if (colon1) {
            char *path_start = colon1 + 1;
            char *colon2 = strchr(path_start, ':');
            if (colon2) {
                /* path is between colon1+1 and colon2 */
                size_t plen = (size_t)(colon2 - path_start);
                if (plen > 0 && plen < sizeof(services[n_services].path)) {
                    memcpy(services[n_services].path, path_start, plen);
                    services[n_services].path[plen] = '\0';
                }
                if (strncmp(colon2 + 1, "direct", 6) == 0)
                    services[n_services].direct = 1;
            } else {
                /* only a path, no flags */
                size_t plen = strlen(path_start);
                if (plen > 0 && plen < sizeof(services[n_services].path)) {
                    memcpy(services[n_services].path, path_start, plen);
                    services[n_services].path[plen] = '\0';
                }
            }
        }
        n_services++;
    }
    fclose(f);
}

/* Return port for named service, or -1 if not found */
static int find_service(const char *name) {
    for (int i = 0; i < n_services; i++)
        if (strcmp(services[i].name, name) == 0)
            return services[i].port;
    return -1;
}

/* Return Service* for named service, or NULL if not found */
static Service *find_service_full(const char *name) {
    for (int i = 0; i < n_services; i++)
        if (strcmp(services[i].name, name) == 0)
            return &services[i];
    return NULL;
}

/* Add the "freetz" service from mod.cfg if missing from config */
static void ensure_freetz_service(void) {
    if (find_service("freetz") >= 0)
        return;
    if (n_services >= MAX_SERVICES)
        return;
    strncpy(services[n_services].name, "freetz", MAX_NAME_LEN - 1);
    services[n_services].name[MAX_NAME_LEN - 1] = '\0';
    services[n_services].port   = get_freetz_port();
    strncpy(services[n_services].path, "/", sizeof(services[n_services].path) - 1);
    services[n_services].direct = 0;
    n_services++;
}

/* ------------------------------------------------------------------
 * HTML-escape: write HTML-safe version of s into out (outsz bytes)
 * ------------------------------------------------------------------ */
static void html_esc(const char *s, char *out, int outsz) {
    int i = 0;
    while (*s && i < outsz - 7) {
        switch (*s) {
            case '&':  memcpy(out+i, "&amp;",  5); i+=5; break;
            case '<':  memcpy(out+i, "&lt;",   4); i+=4; break;
            case '>':  memcpy(out+i, "&gt;",   4); i+=4; break;
            case '"':  memcpy(out+i, "&quot;", 6); i+=6; break;
            default:   out[i++] = *s; break;
        }
        s++;
    }
    out[i] = '\0';
}

/* ------------------------------------------------------------------
 * Emit HTML index of available services
 * ------------------------------------------------------------------ */
static void show_index(const char *script_name, const char *req_host) {
    /* Extract bare hostname from req_host (strip :port if present) */
    char bare_host[256];
    strncpy(bare_host, req_host, sizeof(bare_host) - 1);
    bare_host[sizeof(bare_host) - 1] = '\0';
    char *colon_h = strchr(bare_host, ':');
    if (colon_h) *colon_h = '\0';

    printf("Status: 200 OK\r\n"
           "Content-Type: text/html; charset=UTF-8\r\n"
           "\r\n");
    printf("<!DOCTYPE html>\n<html><head>\n"
           "<meta charset=\"UTF-8\">\n"
           "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n"
           "<title>Freetz Gateway</title>\n"
           "<style>"
           "body{font-family:sans-serif;max-width:700px;margin:40px auto;padding:0 16px}"
           "h1{font-size:1.4em}table{border-collapse:collapse;width:100%%}"
           "th,td{border:1px solid #ccc;padding:6px 10px;text-align:left}"
           "th{background:#f0f0f0}a{text-decoration:none;color:#06c}"
           ".badge{font-size:.75em;padding:2px 6px;border-radius:3px;font-weight:bold}"
           ".proxy{background:#e8f4e8;color:#256325}"
           ".direct{background:#fff3cd;color:#856404}"
           "</style>\n</head><body>\n"
           "<h1>Freetz Gateway</h1>\n"
           "<table><tr><th>Service</th><th>Port</th><th>Type</th><th>Link</th></tr>\n");

    for (int i = 0; i < n_services; i++) {
        char sname[256], spath[512];
        html_esc(services[i].name, sname, (int)sizeof(sname));
        html_esc(services[i].path, spath, (int)sizeof(spath));

        if (services[i].direct) {
            /* Direct HTTP link — bypasses this proxy entirely */
            printf("<tr><td>%s</td><td>%d</td>"
                   "<td><span class=\"badge direct\">HTTP direct</span></td>"
                   "<td><a href=\"http://%s:%d%s\">http://%s:%d%s</a></td></tr>\n",
                   sname, services[i].port,
                   bare_host, services[i].port, spath,
                   bare_host, services[i].port, spath);
        } else {
            /* Proxied through this CGI over HTTPS */
            printf("<tr><td>%s</td><td>%d</td>"
                   "<td><span class=\"badge proxy\">HTTPS proxy</span></td>"
                   "<td><a href=\"https://%s%s?service=%s\">https://%s%s?service=%s</a></td></tr>\n",
                   sname, services[i].port,
                   req_host, script_name, sname,
                   req_host, script_name, sname);
        }
    }
    printf("</table>\n"
           "<p style=\"font-size:.85em;color:#666;margin-top:1em\">"
           "<b>HTTPS proxy</b>: served through this gateway (REST based approach).<br>"
           "<b>HTTP direct</b>: opened directly on the local network (use for WebSocket, web streaming)."
           "</p>\n"
           "</body></html>\n");
    fflush(stdout);
}

/* ------------------------------------------------------------------
 * Send a simple error page as CGI response
 * ------------------------------------------------------------------ */
static void cgi_error(int status, const char *title, const char *body) {
    printf("Status: %d %s\r\n"
           "Content-Type: text/plain\r\n"
           "\r\n"
           "%s\n", status, title, body);
    fflush(stdout);
}
/* ------------------------------------------------------------------
 * Decode HTML entities in-place: &amp; &lt; &gt; &quot; &apos;
 * and numeric &#nn; / &#xhh; references.
 * Used before URL-encoding so that &amp;foo=bar → &foo=bar → %26foo=bar
 * instead of the double-encoding &amp;foo=bar → %26amp;foo=bar.
 * ------------------------------------------------------------------ */
static void html_entity_decode(char *s) {
    char *r = s, *w = s;
    while (*r) {
        if (*r != '&') { *w++ = *r++; continue; }
        /* try named entities */
        if (strncmp(r, "&amp;",  5) == 0) { *w++ = '&';  r += 5; }
        else if (strncmp(r, "&lt;",   4) == 0) { *w++ = '<';  r += 4; }
        else if (strncmp(r, "&gt;",   4) == 0) { *w++ = '>';  r += 4; }
        else if (strncmp(r, "&quot;", 6) == 0) { *w++ = '"';  r += 6; }
        else if (strncmp(r, "&apos;", 6) == 0) { *w++ = '\''; r += 6; }
        else if (strncmp(r, "&#x", 3) == 0 || strncmp(r, "&#X", 3) == 0) {
            /* &#xHH; hex numeric */
            char *end = NULL;
            long v = strtol(r + 3, &end, 16);
            if (end && *end == ';' && v > 0 && v < 128) {
                *w++ = (char)v; r = end + 1;
            } else { *w++ = *r++; }
        } else if (strncmp(r, "&#", 2) == 0) {
            /* &#DDD; decimal numeric */
            char *end = NULL;
            long v = strtol(r + 2, &end, 10);
            if (end && *end == ';' && v > 0 && v < 128) {
                *w++ = (char)v; r = end + 1;
            } else { *w++ = *r++; }
        } else {
            *w++ = *r++;
        }
    }
    *w = '\0';
}

/* ------------------------------------------------------------------
 * URL-encode chars that would break a query-string param value.
 * Encodes: ? & # % + space.  Leaves / unencoded for readability.
 * ------------------------------------------------------------------ */
static void url_path_encode(const char *src, char *dst, int dstsz) {
    int i = 0;
    while (*src && i < dstsz - 4) {
        unsigned char c = (unsigned char)*src;
        if (c == '?' || c == '&' || c == '#' || c == '%' || c == '+' || c == ' ') {
            i += snprintf(dst + i, (size_t)(dstsz - i), "%%%02X", c);
        } else {
            dst[i++] = (char)c;
        }
        src++;
    }
    dst[i] = '\0';
}

/* Percent-encode a full URL for embedding as a query string parameter value.
 * Encodes everything except RFC-3986 unreserved chars [A-Za-z0-9-._~]. */
static void url_full_encode(const char *src, char *dst, int dstsz) {
    int i = 0;
    while (*src && i < dstsz - 4) {
        unsigned char c = (unsigned char)*src;
        if ((c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') ||
            c == '-' || c == '_' || c == '.' || c == '~') {
            dst[i++] = (char)c;
        } else {
            i += snprintf(dst + i, (size_t)(dstsz - i), "%%%02X", c);
        }
        src++;
    }
    dst[i] = '\0';
}

/* ------------------------------------------------------------------
 * Rewrite URL refs in an HTML or CSS body.
 *
 * Patterns handled:
 *   ="/path"  ='/path'              absolute-path (href, src, action, …)
 *   ="?qs"    ='?qs'               query-relative (action="?start", etc.)
 *   url(/path  url('/path  url("/path   CSS absolute-path
 *
 * For absolute paths:
 *   - If the path is a prefix-match for a "direct" service, emit a
 *     plain  http://bare_host:PORT/path  link so the browser opens it
 *     directly (avoids broken proxying of WebSocket apps, complex UIs).
 *   - Otherwise wrap as  ?service=NAME&path=<url-encoded>
 *
 * upstream_path is the path component of the current upstream request
 * (may include a '?' query part).  Its base (up to '?') is used to
 * build the combined URL for query-relative rewrites.
 *
 * bare_host is the hostname without port (e.g. "fritz.box").
 *
 * Returns number of bytes written to g_body_out.
 * ------------------------------------------------------------------ */

/* Returns 1 if the pattern contains any glob metacharacter (* or ?). */
static int path_has_glob(const char *pattern) {
    return strpbrk(pattern, "*?") != NULL;
}

/* Score a matching pattern for specificity (higher = more specific).
 * For plain-prefix patterns: the prefix length itself.
 * For glob patterns: the length of the literal prefix before the first
 * wildcard — a tighter literal prefix beats a shorter one. */
static size_t path_score(const char *pattern) {
    const char *w = strpbrk(pattern, "*?");
    return w ? (size_t)(w - pattern) : strlen(pattern);
}

/* Longest-prefix / best-glob match: return the direct Service* whose
 * configured path either is a plain prefix of url_path OR matches it
 * via fnmatch(3) glob semantics.  Paths of length <= 1 ("/") are
 * skipped to avoid catching everything.
 *
 * Scoring: the service with the longest literal-prefix score wins;
 * ties go to the longer overall pattern string. */
static Service *find_direct_service_for_path(const char *url_path) {
    Service *best       = NULL;
    size_t   best_score = 0;
    size_t   best_len   = 0;
    for (int i = 0; i < n_services; i++) {
        if (!services[i].direct) continue;
        const char *sp    = services[i].path;
        size_t      splen = strlen(sp);
        if (splen <= 1) continue;   /* skip bare "/" */
        int matched;
        if (path_has_glob(sp)) {
            /* Glob pattern: full-path match via fnmatch (FNM_PATHNAME so
             * '*' does NOT cross '/' boundaries, matching shell behaviour;
             * drop the flag if you want cross-directory globs). */
            matched = (fnmatch(sp, url_path, FNM_PATHNAME) == 0);
        } else {
            /* Plain prefix match (legacy behaviour). */
            matched = (strncmp(url_path, sp, splen) == 0);
        }
        if (matched) {
            size_t score = path_score(sp);
            if (score > best_score || (score == best_score && splen > best_len)) {
                best       = &services[i];
                best_score = score;
                best_len   = splen;
            }
        }
    }
    return best;
}

/* ------------------------------------------------------------------
 * Resolve a relative URL path against the directory part of base_path.
 * E.g. base="/style/evo/base.css", rel="../common.css" → "/style/common.css"
 * If rel already starts with '/' it is returned as-is.
 * ------------------------------------------------------------------ */
static void resolve_relative_path(const char *base, const char *rel,
                                   char *out, int outsz)
{
    if (rel[0] == '/') {
        strncpy(out, rel, (size_t)(outsz - 1));
        out[outsz - 1] = '\0';
        return;
    }

    /* Strip filename from base to get directory (keep trailing '/') */
    char dir[512];
    strncpy(dir, base, sizeof(dir) - 1);
    dir[sizeof(dir) - 1] = '\0';
    char *sl = strrchr(dir, '/');
    if (sl) sl[1] = '\0';
    else   { dir[0] = '/'; dir[1] = '\0'; }

    /* Concatenate directory + relative path */
    char combined[1024];
    snprintf(combined, sizeof(combined), "%s%s", dir, rel);

    /* Normalise: process '.' and '..' segments */
    /* Split into segments, skip '.' and pop on '..' */
    char  tmp[1024];
    strncpy(tmp, combined, sizeof(tmp) - 1);
    tmp[sizeof(tmp) - 1] = '\0';

    const char *segs[64];
    int  nseg = 0;
    char *p   = tmp;
    while (*p) {
        if (*p == '/') { p++; continue; }
        char *nxt = strchr(p, '/');
        if (nxt) *nxt = '\0';
        if (strcmp(p, "..") == 0) {
            if (nseg > 0) nseg--;
        } else if (strcmp(p, ".") != 0) {
            if (nseg < 64) segs[nseg++] = p;
        }
        p = nxt ? nxt + 1 : p + strlen(p);
    }

    /* Reassemble */
    int pos = 0;
    for (int k = 0; k < nseg && pos < outsz - 2; k++) {
        out[pos++] = '/';
        int slen = (int)strlen(segs[k]);
        if (pos + slen >= outsz - 1) slen = outsz - pos - 2;
        memcpy(out + pos, segs[k], (size_t)slen);
        pos += slen;
    }
    if (pos == 0) { out[pos++] = '/'; }
    out[pos] = '\0';
}

static size_t rewrite_body(const char *in, size_t inlen,
                           const char *service_name,
                           const char *upstream_path,
                           const char *bare_host) {
    char  *out  = g_body_out;
    size_t outsz = BODY_OUT_MAX;
    size_t o = 0, i = 0;

    /* Strip query-string from upstream_path to get the base path */
    char upstream_base[512];
    const char *qmark = strchr(upstream_path, '?');
    if (qmark) {
        size_t blen2 = (size_t)(qmark - upstream_path);
        if (blen2 >= sizeof(upstream_base)) blen2 = sizeof(upstream_base) - 1;
        memcpy(upstream_base, upstream_path, blen2);
        upstream_base[blen2] = '\0';
    } else {
        strncpy(upstream_base, upstream_path, sizeof(upstream_base) - 1);
        upstream_base[sizeof(upstream_base) - 1] = '\0';
    }

    /* Tracks the ACE editor CDN base URL (e.g. https://cdnjs.cloudflare.com/.../ace/1.23.4/).
     * Once ace.js is seen, ace_inject_pending=1 so we inject ace.config.set('basePath',...)
     * immediately after the </script> tag that loaded ace.js -- before any inline init code. */
    char ace_cdn_base[256] = "";
    int  ace_inject_pending = 0;

    while (i < inlen && o + 512 < outsz) {
        /* Strip <link rel="manifest" ...> — the Fritz HTTPS gateway's CSP uses
         * default-src 'none' as manifest-src fallback, so a proxied webmanifest
         * link is always blocked by the browser.  Drop the tag entirely. */
        if (in[i] == '<' && i + 5 < inlen &&
            strncasecmp(in + i, "<link", 5) == 0 &&
            (in[i+5] == ' ' || in[i+5] == '\t' || in[i+5] == '\n' ||
             in[i+5] == '\r' || in[i+5] == '>')) {
            size_t te = i + 5;
            while (te < inlen && in[te] != '>') te++;
            /* Detect rel="manifest" or rel='manifest' inside the tag */
            int strip_link = 0;
            for (size_t k = i; k + 13 < te && !strip_link; k++) {
                if (strncasecmp(in + k, "rel=", 4) != 0) continue;
                size_t vk = k + 4;
                while (vk < te && (in[vk] == ' ' || in[vk] == '\t')) vk++;
                if (vk < te) {
                    char q2 = (in[vk] == '"' || in[vk] == '\'') ? in[vk++] : 0;
                    (void)q2;
                    if (strncasecmp(in + vk, "manifest", 8) == 0)
                        strip_link = 1;
                }
                break;
            }
            if (strip_link) { i = te + 1; continue; }
        }

        /* pattern: ="https://..." or ='https://...' — absolute external HTTPS URL
         * (e.g. CDN resources: <script src="https://cdn..."> <link href="https://cdn...">)
         * Rewrite to ?service=cdn&url=<encoded> so the browser fetches it through
         * our proxy under 'self' origin, satisfying AVM's CSP "script-src 'self'".
         * NOTE: Only https:// is matched.  Plain http:// links (e.g. navigation
         * <a href="http://fritz.box:PORT/"> are left untouched so they open directly. */
        if (in[i] == '=' &&
            i + 2 < inlen &&
            (in[i+1] == '"' || in[i+1] == '\'') &&
            strncasecmp(in + i + 2, "https://", 8) == 0) {

            char q = in[i+1];
            size_t vs = i + 2;
            size_t ve = vs;
            while (ve < inlen && in[ve] != q) ve++;

            char raw[2048] = "";
            size_t vlen = ve - vs;
            if (vlen < sizeof(raw)) { memcpy(raw, in + vs, vlen); raw[vlen] = '\0'; }

            char enc[4096];
            url_full_encode(raw, enc, (int)sizeof(enc));

            /* Capture ACE CDN base path; will inject ace.config.set after </script> */
            if (ace_cdn_base[0] == '\0') {
                size_t rlen2 = strlen(raw);
                /* Match URLs ending with /ace.js (e.g. .../ace/1.23.4/ace.js) */
                if (rlen2 > 7 &&
                    (strncmp(raw + rlen2 - 7, "/ace.js", 7) == 0 ||
                     strncmp(raw + rlen2 - 11, "/ace.min.js", 11) == 0)) {
                    const char *last = strrchr(raw, '/');
                    if (last) {
                        size_t blen3 = (size_t)(last - raw) + 1; /* include trailing '/' */
                        if (blen3 < sizeof(ace_cdn_base)) {
                            memcpy(ace_cdn_base, raw, blen3);
                            ace_cdn_base[blen3] = '\0';
                        }
                    }
                    ace_inject_pending = 1;
                }
            }

            int w = snprintf(out + o, outsz - o, "=%c?service=cdn&url=%s%c",
                              q, enc, q);
            if (w > 0) o += (size_t)w;
            i = ve + 1;
            continue;
        }

        /* pattern: ="?qs" or ='?qs'  — query-relative URL (e.g. action="?start") */
        if (in[i] == '=' &&
            i + 2 < inlen &&
            (in[i+1] == '"' || in[i+1] == '\'') &&
            in[i+2] == '?') {

            char q = in[i+1];
            size_t vs = i + 2; /* points at '?' */
            size_t ve = vs + 1;
            while (ve < inlen && in[ve] != q) ve++;

            /* qs_suffix = everything after the '?', before closing quote */
            char qs_suffix[1024] = "";
            size_t qslen = ve - vs - 1;
            if (qslen < sizeof(qs_suffix)) {
                memcpy(qs_suffix, in + vs + 1, qslen);
                qs_suffix[qslen] = '\0';
            }

            /* HTML-decode entities in the query suffix before URL-encoding
             * (prevents &amp;key=val → %26amp;key=val double-encoding) */
            html_entity_decode(qs_suffix);

            /* combined = upstream_base?qs_suffix */
            char combined[2048];
            if (qs_suffix[0])
                snprintf(combined, sizeof(combined), "%s?%s", upstream_base, qs_suffix);
            else
                strncpy(combined, upstream_base, sizeof(combined) - 1);
            combined[sizeof(combined) - 1] = '\0';

            char enc[2048];
            url_path_encode(combined, enc, (int)sizeof(enc));

            int w = snprintf(out + o, outsz - o, "=%c?service=%s&path=%s%c",
                              q, service_name, enc, q);
            if (w > 0) o += (size_t)w;
            i = ve + 1;
            continue;
        }

        /* pattern: ="/ or ='/ */
        if (in[i] == '=' &&
            i + 2 < inlen &&
            (in[i+1] == '"' || in[i+1] == '\'') &&
            in[i+2] == '/' &&
            (i + 3 >= inlen || in[i+3] != '/')) {

            char q = in[i+1];
            size_t vs = i + 2;
            size_t ve = vs;
            while (ve < inlen && in[ve] != q) ve++;

            char raw[1024] = "";
            size_t vlen = ve - vs;
            if (vlen < sizeof(raw)) { memcpy(raw, in + vs, vlen); raw[vlen] = '\0'; }
            html_entity_decode(raw);

            Service *dsvc = find_direct_service_for_path(raw);
            int w;
            if (dsvc) {
                /* Path belongs to a direct service — emit plain http:// link */
                w = snprintf(out + o, outsz - o, "=%chttp://%s:%d%s%c",
                              q, bare_host, dsvc->port, raw, q);
            } else {
                char enc[2048];
                url_path_encode(raw, enc, (int)sizeof(enc));
                w = snprintf(out + o, outsz - o, "=%c?service=%s&path=%s%c",
                              q, service_name, enc, q);
            }
            if (w > 0) o += (size_t)w;
            i = ve + 1;
            continue;
        }

        /* pattern: url(/ or url('/ or url("/  — and relative: url(../ url(path) */
        /* Word-boundary guard: skip if 'url' is a suffix of a longer identifier
         * (e.g. URL.createObjectURL(blob) must NOT be treated as a CSS url()).
         * Also skip JS constructors: "new URL(" and method chains "obj.URL(". */
        if (i + 4 <= inlen &&
            (i == 0 || (!isalnum((unsigned char)in[i-1]) && in[i-1] != '.')) &&
            !(i >= 4 && strncasecmp(in + i - 4, "new ", 4) == 0) &&
            tolower((unsigned char)in[i])   == 'u' &&
            tolower((unsigned char)in[i+1]) == 'r' &&
            tolower((unsigned char)in[i+2]) == 'l' &&
            in[i+3] == '(') {

            size_t j = i + 4;
            char q2 = 0;
            if (j < inlen && (in[j] == '"' || in[j] == '\'')) q2 = in[j++];

            if (j < inlen && in[j] == '/' && (j + 1 >= inlen || in[j+1] != '/')) {
                /* Absolute path: url(/foo) */
                size_t vs2 = j;
                size_t ve2 = vs2;
                char ec = q2 ? q2 : ')';
                while (ve2 < inlen && in[ve2] != ec && in[ve2] != ')') ve2++;

                char raw2[1024] = "";
                size_t vlen2 = ve2 - vs2;
                if (vlen2 < sizeof(raw2)) { memcpy(raw2, in + vs2, vlen2); raw2[vlen2] = '\0'; }
                html_entity_decode(raw2);

                const char *qs2 = q2 == '"' ? "\"" : (q2 == '\'' ? "'" : "");
                Service *dsvc2 = find_direct_service_for_path(raw2);
                int w2;
                if (dsvc2) {
                    w2 = snprintf(out + o, outsz - o, "url(%shttp://%s:%d%s%s",
                                   qs2, bare_host, dsvc2->port, raw2, qs2);
                } else {
                    char enc2[2048];
                    url_path_encode(raw2, enc2, (int)sizeof(enc2));
                    w2 = snprintf(out + o, outsz - o, "url(%s?service=%s&path=%s%s",
                                   qs2, service_name, enc2, qs2);
                }
                if (w2 > 0) o += (size_t)w2;
                i = ve2;
                continue;
            } else if (j < inlen && in[j] != ')' && in[j] != '#' &&
                       strncasecmp(in + j, "http",       4) != 0 &&
                       strncasecmp(in + j, "data:",      5) != 0 &&
                       strncasecmp(in + j, "javascript:",11) != 0) {
                /* Relative path: url(../foo.css)  url(foo.css)  etc.
                 * Resolve against the upstream file's directory. */
                size_t vs2r = j;
                size_t ve2r = vs2r;
                char ecr = q2 ? q2 : ')';
                while (ve2r < inlen && in[ve2r] != ecr && in[ve2r] != ')') ve2r++;

                char raw2r[1024] = "";
                size_t vlen2r = ve2r - vs2r;
                if (vlen2r > 0 && vlen2r < sizeof(raw2r)) {
                    memcpy(raw2r, in + vs2r, vlen2r);
                    raw2r[vlen2r] = '\0';
                    html_entity_decode(raw2r);

                    char resolved[1024];
                    resolve_relative_path(upstream_base, raw2r,
                                          resolved, (int)sizeof(resolved));

                    const char *qs2r = q2 == '"' ? "\"" : (q2 == '\'' ? "'" : "");
                    Service *dsvc2r = find_direct_service_for_path(resolved);
                    int w2r;
                    if (dsvc2r) {
                        w2r = snprintf(out + o, outsz - o,
                                       "url(%shttp://%s:%d%s%s",
                                       qs2r, bare_host, dsvc2r->port,
                                       resolved, qs2r);
                    } else {
                        char enc2r[2048];
                        url_path_encode(resolved, enc2r, (int)sizeof(enc2r));
                        w2r = snprintf(out + o, outsz - o,
                                       "url(%s?service=%s&path=%s%s",
                                       qs2r, service_name, enc2r, qs2r);
                    }
                    if (w2r > 0) o += (size_t)w2r;
                    i = ve2r + (q2 ? 1 : 0);
                    continue;
                }
            }
        }

        /* pattern: ('/path'  or ("/path"  — absolute path in JS function call
         * argument.  Handles window.open('/path', ...), location.assign('/path')
         * etc.  The url('...') CSS pattern above has already consumed any
         * url( prefix so those won't reach here.
         *
         * Negative-lookbehind: skip when ( is an argument to a string-predicate
         * or DOM method where the path is a search needle, not a navigation target:
         * .includes( .indexOf( .lastIndexOf( .startsWith( .endsWith( .match(
         * .matchAll( .test( .search( .split( .replace( .replaceAll( .contains(
         * .has( .get( .set( .getAttribute( .setAttribute( .querySelector(
         * .querySelectorAll( .closest( .matches( .find( .filter( .from( */
        if (in[i] == '(' &&
            i + 3 < inlen &&
            (in[i+1] == '"' || in[i+1] == '\'') &&
            in[i+2] == '/' &&
            (i + 3 >= inlen || in[i+3] != '/')) {

            /* scan backwards over the identifier that precedes ( */
            {
                static const char *skip_methods[] = {
                    "includes", "indexOf", "lastIndexOf", "startsWith", "endsWith",
                    "match", "matchAll", "test", "search", "split", "replace",
                    "replaceAll", "contains", "has", "get", "set",
                    "getAttribute", "setAttribute", "querySelector",
                    "querySelectorAll", "closest", "matches", "find",
                    "filter", "from", NULL
                };
                size_t bi = i;
                while (bi > 0 &&
                       (isalnum((unsigned char)in[bi-1]) || in[bi-1] == '_'))
                    bi--;
                size_t idlen = i - bi;
                int skip_j = 0;
                for (int si = 0; skip_methods[si] && !skip_j; si++) {
                    size_t sl = strlen(skip_methods[si]);
                    if (idlen == sl &&
                        strncmp(in + bi, skip_methods[si], sl) == 0)
                        skip_j = 1;
                }
                if (skip_j) { out[o++] = in[i++]; continue; }
            }

            char qj = in[i+1];
            size_t vsj = i + 2;
            size_t vej = vsj;
            while (vej < inlen && in[vej] != qj) vej++;

            char rawj[1024] = "";
            size_t vlenj = vej - vsj;
            if (vlenj > 0 && vlenj < sizeof(rawj)) {
                memcpy(rawj, in + vsj, vlenj);
                rawj[vlenj] = '\0';
                html_entity_decode(rawj);

                Service *dsvj = find_direct_service_for_path(rawj);
                int wj;
                if (dsvj) {
                    wj = snprintf(out + o, outsz - o, "(%chttp://%s:%d%s%c",
                                  qj, bare_host, dsvj->port, rawj, qj);
                } else {
                    char encj[2048];
                    url_path_encode(rawj, encj, (int)sizeof(encj));
                    wj = snprintf(out + o, outsz - o, "(%c?service=%s&path=%s%c",
                                  qj, service_name, encj, qj);
                }
                if (wj > 0) o += (size_t)wj;
                i = vej + 1;
                continue;
            }
        }

        /* pattern: url=/path  url="/path"  url='/path'
         * Handles <meta http-equiv="refresh" content="N;url=/path">
         * (the content attribute value starts with a digit so the ="/"
         * pattern never fires; we need to catch the url= part inside it).
         * Only triggered when preceded by ; or whitespace to avoid false
         * matches on JS variable names that happen to end in "url". */
        if (i + 4 < inlen && i > 0 &&
            (in[i-1] == ';' || in[i-1] == ' ' || in[i-1] == '\t' ||
             in[i-1] == '\n' || in[i-1] == '\r') &&
            tolower((unsigned char)in[i])   == 'u' &&
            tolower((unsigned char)in[i+1]) == 'r' &&
            tolower((unsigned char)in[i+2]) == 'l' &&
            in[i+3] == '=') {

            char q3 = 0;
            size_t vs3 = i + 4;
            if (vs3 < inlen && (in[vs3] == '"' || in[vs3] == '\''))
                q3 = in[vs3++];

            if (vs3 < inlen && in[vs3] == '/' &&
                (vs3 + 1 >= inlen || in[vs3 + 1] != '/')) {

                size_t ve3 = vs3;
                /* end at the matching inner quote (if any), or outer
                 * attribute delimiter, > or whitespace */
                while (ve3 < inlen &&
                       (q3 ? in[ve3] != q3 : 1) &&
                       in[ve3] != '"' && in[ve3] != '\'' &&
                       in[ve3] != '>' && in[ve3] != ' ' &&
                       in[ve3] != '\t' && in[ve3] != '\n') ve3++;

                char raw3[1024] = "";
                size_t vlen3 = ve3 - vs3;
                if (vlen3 < sizeof(raw3)) {
                    memcpy(raw3, in + vs3, vlen3); raw3[vlen3] = '\0';
                }
                html_entity_decode(raw3);

                const char *q3s = q3 == '"' ? "\"" : (q3 == '\'' ? "'" : "");
                Service *dsvc3 = find_direct_service_for_path(raw3);
                int w3;
                if (dsvc3) {
                    w3 = snprintf(out + o, outsz - o, "url=%shttp://%s:%d%s%s",
                                  q3s, bare_host, dsvc3->port, raw3, q3s);
                } else {
                    char enc3[2048];
                    url_path_encode(raw3, enc3, (int)sizeof(enc3));
                    w3 = snprintf(out + o, outsz - o, "url=%s?service=%s&path=%s%s",
                                  q3s, service_name, enc3, q3s);
                }
                if (w3 > 0) o += (size_t)w3;
                i = ve3 + (q3 ? 1 : 0); /* skip closing inner quote */
                continue;
            }
        }

        /* pattern: : '/path'  or : "/path"
         * JS object-literal property value that is an absolute path, e.g.:
         *   cgiUrl: '/cgi-bin/conf/rtorrent',
         *   baseUrl: "/mod/cgi-bin/foo",
         * Triggered when the character before the opening quote (skipping spaces)
         * is a colon (':'), which is the JS object key/value separator.
         * Negative-lookbehind: same skip-method list as pattern 7 is not needed
         * here because the colon separator is unambiguous in this context.
         * We also skip ':/' (no-space) which could be a protocol literal like
         * 'https:' — only fire when the colon is NOT immediately followed by '/'
         * (i.e., there is at least a space or the quote is right after ':'). */
        if ((in[i] == '\'' || in[i] == '"') &&
            i + 2 < inlen &&
            in[i+1] == '/' &&
            (i + 2 >= inlen || in[i+2] != '/')) {
            /* scan backwards skipping spaces to find ':' preceded by a word char.
             * This distinguishes  key: '/path'  (object literal, fire)  from
             * cond ? x : '/path'  (ternary, skip — ':' preceded by ' or ) etc.) */
            size_t bk = i;
            while (bk > 0 && (in[bk-1] == ' ' || in[bk-1] == '\t')) bk--;
            if (bk > 0 && in[bk-1] == ':') {
                /* require that ':' itself is preceded by a word char (identifier end) */
                int colon_ok = (bk >= 2 &&
                                (isalnum((unsigned char)in[bk-2]) || in[bk-2] == '_' ||
                                 in[bk-2] == '"' || in[bk-2] == '\''));
                if (colon_ok) {
                    char qk = in[i];
                    size_t vsk = i + 1;
                    size_t vek = vsk;
                    while (vek < inlen && in[vek] != qk) vek++;

                    char rawk[1024] = "";
                    size_t vlenk = vek - vsk;
                    if (vlenk > 0 && vlenk < sizeof(rawk)) {
                        memcpy(rawk, in + vsk, vlenk);
                        rawk[vlenk] = '\0';
                        html_entity_decode(rawk);

                        Service *dsvk = find_direct_service_for_path(rawk);
                        int wk;
                        if (dsvk) {
                            wk = snprintf(out + o, outsz - o, "%chttp://%s:%d%s%c",
                                          qk, bare_host, dsvk->port, rawk, qk);
                        } else {
                            char enck[2048];
                            url_path_encode(rawk, enck, (int)sizeof(enck));
                            wk = snprintf(out + o, outsz - o,
                                          "%c?service=%s&path=%s%c",
                                          qk, service_name, enck, qk);
                        }
                        if (wk > 0) o += (size_t)wk;
                        i = vek + 1;
                        continue;
                    }
                } /* colon_ok */
            } /* in[bk-1] == ':' */
        }

        /* pattern: </script>  -- if ace.js was just loaded, inject basePath config
         * immediately after this closing tag so it runs before any inline init code.
         *
         * We set basePath to a RELATIVE proxy URL (?service=cdn&url=<enc_base>)
         * rather than the direct CDN URL.  When ACE does basePath + 'theme-monokai.js'
         * the result is "?service=cdn&url=...%2Ftheme-monokai.js" which the browser
         * resolves against the current page origin (our CGI), so the CDN proxy serves
         * every ACE module file.  This avoids ACE overriding our set() with the
         * auto-detected basePath it derives from document.currentScript.src. */
        if (ace_inject_pending &&
            strncasecmp(in + i, "</script>", 9) == 0 &&
            o + 640 < outsz) {
            /* emit </script> first */
            memcpy(out + o, "</script>", 9); o += 9;
            i += 9;
            /* URL-encode ace_cdn_base for embedding as a query param value */
            char enc_ace_base[512] = "";
            url_full_encode(ace_cdn_base, enc_ace_base, (int)sizeof(enc_ace_base));
            int wace = snprintf(out + o, outsz - o,
                "<script>ace.config.set('basePath','?service=cdn&url=%s');"
                "ace.config.set('modePath','?service=cdn&url=%s');"
                "ace.config.set('themePath','?service=cdn&url=%s');"
                "ace.config.set('workerPath','?service=cdn&url=%s');"
                "</script>",
                enc_ace_base, enc_ace_base, enc_ace_base, enc_ace_base);
            if (wace > 0) o += (size_t)wace;
            ace_inject_pending = 0;
            continue;
        }

        out[o++] = in[i++];
    }
    /* copy any remaining bytes that didn't fit in the pattern scan */
    while (i < inlen && o < outsz - 1) out[o++] = in[i++];
    return o;
}

/* ------------------------------------------------------------------
 * Guess Content-Type from a URL's file extension.
 * ------------------------------------------------------------------ */
static const char *guess_content_type(const char *url) {
    /* Strip query string first */
    const char *q = strchr(url, '?');
    size_t ulen = q ? (size_t)(q - url) : strlen(url);

    /* Find last dot within the path portion */
    const char *dot = NULL;
    for (size_t k = 0; k < ulen; k++)
        if (url[k] == '.') dot = url + k;

    if (dot) {
        if (strncasecmp(dot, ".js",   3) == 0) return "application/javascript; charset=UTF-8";
        if (strncasecmp(dot, ".css",  4) == 0) return "text/css; charset=UTF-8";
        if (strncasecmp(dot, ".html", 5) == 0) return "text/html; charset=UTF-8";
        if (strncasecmp(dot, ".json", 5) == 0) return "application/json";
        if (strncasecmp(dot, ".svg",  4) == 0) return "image/svg+xml";
        if (strncasecmp(dot, ".png",  4) == 0) return "image/png";
        if (strncasecmp(dot, ".ico",  4) == 0) return "image/x-icon";
        if (strncasecmp(dot, ".woff2",6) == 0) return "font/woff2";
        if (strncasecmp(dot, ".woff", 5) == 0) return "font/woff";
    }
    return "application/octet-stream";
}

/* ------------------------------------------------------------------
 * Fetch an external URL via curl (has SSL, follows redirects) and
 * stream the response body back to the CGI client.
 *
 * Used for CDN resources (xterm.js etc.) blocked by AVM's CSP when
 * fetched directly, but allowed when served from 'self'.
 * ------------------------------------------------------------------ */
static void do_cdn_proxy(const char *url) {
    DBG("CDN proxy: %s", url);
    /* Only allow http(s):// URLs */
    if (strncmp(url, "https://", 8) != 0 && strncmp(url, "http://", 7) != 0) {
        DBG("CDN denied (not http/https): %s", url);
        cgi_error(400, "Bad Request", "CDN URL must start with http(s)://");
        return;
    }

    /* Escape single-quotes in the URL to prevent shell injection */
    char safe_url[4096] = "";
    size_t si = 0;
    for (const char *p = url; *p && si < sizeof(safe_url) - 5; p++) {
        if (*p == '\'') {
            /* '\'' pattern */
            safe_url[si++] = '\''; safe_url[si++] = '\\';
            safe_url[si++] = '\''; safe_url[si++] = '\'';
        } else {
            safe_url[si++] = *p;
        }
    }
    safe_url[si] = '\0';

    char cmd[5000];
    snprintf(cmd, sizeof(cmd),
             "curl -sfL --max-time 30 --compressed '%s' 2>/dev/null",
             safe_url);

    FILE *fp = popen(cmd, "r");
    if (!fp) {
        cgi_error(502, "Bad Gateway", "curl not available");
        return;
    }

    const char *ct = guess_content_type(url);
    DBG("CDN serving content-type: %s", ct);
    printf("Status: 200 OK\r\n"
           "Content-Type: %s\r\n"
           "Cache-Control: public, max-age=86400\r\n"
           "\r\n", ct);

    char buf[BUF_SIZE];
    size_t n;
    size_t total = 0;
    while ((n = fread(buf, 1, sizeof(buf), fp)) > 0) {
        fwrite(buf, 1, n, stdout);
        total += n;
    }
    fflush(stdout);
    int rc = pclose(fp);
    DBG("CDN done: %zu bytes, curl exit=%d url=%s", total, rc, url);
}

/* ------------------------------------------------------------------
 * Rewrite a manifest.json body so that start_url / scope / id point at
 * the proxy's own URL, and all icon/shortcut "src"/"url" absolute paths
 * are wrapped as proxy requests.
 *
 * JSON fields rewritten:
 *   "start_url": "..."   → "start_url": "SCRIPT?service=SERVICE"
 *   "scope":     "..."   → "scope":     "SCRIPT"
 *   "id":        "..."   → "id":        "SCRIPT"
 *   "src":       "/..."  → "src":       "SCRIPT?service=SERVICE&path=/..."
 *   "url":       "/..."  → "url":       "SCRIPT?service=SERVICE&path=/..."
 *
 * Writes rewritten JSON into g_body_out, returns byte count.
 * ------------------------------------------------------------------ */
static size_t rewrite_manifest(const char *in, size_t inlen,
                                const char *script_name,
                                const char *service_name)
{
    size_t oi = 0;    /* output index into g_body_out */
    size_t outmax = BODY_OUT_MAX;

/* helpers --------------------------------------------------------- */
#define MO_CHAR(c) do { if (oi < outmax-1) g_body_out[oi++] = (char)(c); } while(0)
#define MO_STR(s)  do { const char *_p = (s); \
    while (*_p && oi < outmax-1) g_body_out[oi++] = *_p++; } while(0)
#define MO_MEM(p,n) do { const char *_p2=(p); size_t _n2=(n); \
    size_t _x2; for(_x2=0;_x2<_n2&&oi<outmax-1;_x2++) g_body_out[oi++]=_p2[_x2]; } while(0)
/* ----------------------------------------------------------------- */

    size_t ii = 0;
    while (ii < inlen) {
        char c = in[ii];

        if (c != '"') { MO_CHAR(c); ii++; continue; }

        /* Collect JSON key string: "KEY" */
        size_t ks = ii + 1;
        size_t ke = ks;
        while (ke < inlen && in[ke] != '"') {
            if (in[ke] == '\\') ke++;  /* skip escape */
            ke++;
        }
        if (ke >= inlen) { MO_CHAR(c); ii++; continue; }  /* unterminated */

        size_t klen = ke - ks;
        const char *key = in + ks;

        int is_start_url = (klen == 9 && memcmp(key, "start_url", 9) == 0);
        int is_scope     = (klen == 5 && memcmp(key, "scope",     5) == 0);
        int is_id        = (klen == 2 && memcmp(key, "id",        2) == 0);
        int is_src       = (klen == 3 && memcmp(key, "src",       3) == 0);
        int is_url_field = (klen == 3 && memcmp(key, "url",       3) == 0);

        if (!(is_start_url || is_scope || is_id || is_src || is_url_field)) {
            /* Not a key we care about — copy the opening quote and advance */
            MO_CHAR(c); ii++; continue;
        }

        /* Check that key is followed by  : "VALUE"  (skip whitespace) */
        size_t p = ke + 1;
        while (p < inlen && (in[p]==' '||in[p]=='\t'||in[p]=='\n'||in[p]=='\r')) p++;
        if (p >= inlen || in[p] != ':') { MO_CHAR(c); ii++; continue; }
        p++;  /* skip ':' */
        while (p < inlen && (in[p]==' '||in[p]=='\t')) p++;
        if (p >= inlen || in[p] != '"') { MO_CHAR(c); ii++; continue; }

        /* p now points at opening " of value string */
        size_t vs = p + 1;
        size_t ve = vs;
        while (ve < inlen && in[ve] != '"') {
            if (in[ve] == '\\') ve++;  /* skip escape */
            ve++;
        }
        if (ve >= inlen) { MO_CHAR(c); ii++; continue; }  /* unterminated */

        const char *val  = in + vs;
        size_t      vlen = ve - vs;

        /* Emit  "KEY": "  (key + separator already in source) */
        MO_CHAR('"');
        MO_MEM(key, klen);
        MO_CHAR('"');
        /* Emit the ': ' separator as it appears in the source */
        MO_MEM(in + ke + 1, p - ke - 1);  /* chars between key's " and value's " */
        MO_CHAR('"');  /* opening " of value */

        /* Emit new value */
        if (is_start_url) {
            MO_STR(script_name);
            MO_STR("?service=");
            MO_STR(service_name);
        } else if (is_scope || is_id) {
            MO_STR(script_name);
        } else if ((is_src || is_url_field) && vlen > 0 && val[0] == '/') {
            /* Proxy the absolute path */
            MO_STR(script_name);
            MO_CHAR('?');
            MO_STR("service=");
            MO_STR(service_name);
            MO_CHAR('&');
            MO_STR("path=");
            MO_MEM(val, vlen);
        } else {
            /* Not a rewritable value — keep as-is */
            MO_MEM(val, vlen);
        }

        MO_CHAR('"');  /* closing " of value */
        ii = ve + 1;   /* advance past closing " of value */
    }

#undef MO_CHAR
#undef MO_STR
#undef MO_MEM

    g_body_out[oi] = '\0';
    return oi;
}

static void env_key_to_header(const char *key, char *out, int outsz) {
    /* key starts at index 5 (skip "HTTP_") */
    const char *src = key + 5;
    int i = 0, new_word = 1;
    while (*src && i < outsz - 2) {
        if (*src == '_') {
            out[i++] = '-';
            new_word = 1;
        } else if (new_word) {
            out[i++] = (char)toupper((unsigned char)*src);
            new_word = 0;
        } else {
            out[i++] = (char)tolower((unsigned char)*src);
        }
        src++;
    }
    out[i] = '\0';
}

/* ------------------------------------------------------------------
 * Core proxy: connect to upstream port and relay the request/response.
 *
 * HTML and CSS responses are buffered and rewritten so that absolute
 * path references (href="/...", src="/...", url(/...)) are replaced
 * with proxy URLs (?service=NAME&path=…) unless the path belongs to
 * a "direct" service, in which case a plain http:// link is emitted.
 *
 * Location headers are URL-encoded so that redirects to paths that
 * contain query strings (e.g. /login.cgi?subpage=/&hash=…) round-trip
 * correctly through the ?path= parameter.
 * ------------------------------------------------------------------ */
static void do_proxy(int upstream_port, const char *upstream_path,
                     const char *service_name,
                     const char *method, const char *query_str,
                     const char *content_len, const char *content_type,
                     const char *script_name, const char *req_host,
                     const char *bare_host) {
    extern char **environ;
    char tmp[BUF_SIZE];
    int  n;
    /* Strip Max-Age/Expires from Set-Cookie when no_cookie or (no_internet_cookie && from internet) */
    int strip_cookies = g_no_cookie || (g_no_internet_cookie && g_is_internet);

    int sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) { cgi_error(502, "Bad Gateway", "Cannot create socket"); return; }

    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port   = htons((unsigned short)upstream_port);
    inet_pton(AF_INET, FREETZ_HOST, &addr.sin_addr);

    if (connect(sock, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        cgi_error(502, "Bad Gateway", "Cannot connect to upstream service");
        close(sock);
        return;
    }

    /* ---- Send upstream request ---- */
    if (query_str && query_str[0]) {
        /* upstream_path may already contain '?' if path= included a query */
        char sep = strchr(upstream_path, '?') ? '&' : '?';
        n = snprintf(tmp, sizeof(tmp), "%s %s%c%s HTTP/1.1\r\n",
                     method, upstream_path, sep, query_str);
    } else {
        n = snprintf(tmp, sizeof(tmp), "%s %s HTTP/1.1\r\n",
                     method, upstream_path);
    }
    DBG("  upstream: %s port=%d qs=[%s]", tmp, upstream_port,
        query_str ? query_str : "-");
    write_all(sock, tmp, n);

    n = snprintf(tmp, sizeof(tmp), "Host: %s:%d\r\n", FREETZ_HOST, upstream_port);
    write_all(sock, tmp, n);
    write_str(sock, "Connection: close\r\n");

    for (char **ep = environ; *ep; ep++) {
        if (strncmp(*ep, "HTTP_", 5) != 0) continue;
        if (strncmp(*ep, "HTTP_HOST=",       10) == 0) continue;
        if (strncmp(*ep, "HTTP_CONNECTION=", 16) == 0) continue;
        /* For the Cookie header: freetz's session check uses the greedy sed
         * pattern ".*SID=..." which, when PHPSESSID (or any other *SID=*)
         * cookie is present, matches the WRONG cookie name and extracts the
         * wrong value — causing checklogin() to look for a non-existent file
         * and delete the real session file as a side-effect.
         * Fix: forward ONLY the cookie whose name is exactly "SID". */
        if (strncmp(*ep, "HTTP_COOKIE=", 12) == 0) {
            DBG("  upstream-cookie: %s", *ep);
            const char *c = *ep + 12;
            char sid_val[128] = "";
            /* Walk the semicolon-separated cookie list */
            while (c && *c) {
                while (*c == ' ' || *c == '\t') c++; /* trim whitespace */
                /* exact name match: "SID=" where prev char is start or ';' */
                if (strncmp(c, "SID=", 4) == 0) {
                    const char *vs = c + 4, *ve = vs;
                    while (*ve && *ve != ';') ve++;
                    size_t vlen = ve - vs;
                    if (vlen < sizeof(sid_val)) {
                        memcpy(sid_val, vs, vlen);
                        sid_val[vlen] = '\0';
                    }
                    break;
                }
                while (*c && *c != ';') c++;
                if (*c == ';') c++;
            }
            if (sid_val[0]) {
                n = snprintf(tmp, sizeof(tmp), "Cookie: SID=%s\r\n", sid_val);
                write_all(sock, tmp, n);
            }
            continue; /* skip the generic env→header conversion */
        }
        char *eq = strchr(*ep, '=');
        if (!eq) continue;
        int klen = (int)(eq - *ep);
        if (klen >= 128) continue;
        char key[128];
        memcpy(key, *ep, (size_t)klen); key[klen] = '\0';
        char hdr_name[128];
        env_key_to_header(key, hdr_name, (int)sizeof(hdr_name));
        n = snprintf(tmp, sizeof(tmp), "%s: %s\r\n", hdr_name, eq + 1);
        write_all(sock, tmp, n);
    }
    if (content_type && content_type[0]) {
        n = snprintf(tmp, sizeof(tmp), "Content-Type: %s\r\n", content_type);
        write_all(sock, tmp, n);
    }
    if (content_len && content_len[0]) {
        n = snprintf(tmp, sizeof(tmp), "Content-Length: %s\r\n", content_len);
        write_all(sock, tmp, n);
    }
    write_str(sock, "\r\n");

    if (content_len && content_len[0]) {
        long body_len = atol(content_len);
        if (g_tunnel_body_len > 0) {
            /* Method-tunneled body: send from buffer, not stdin */
            write_all(sock, g_tunnel_body, (int)g_tunnel_body_len);
        } else {
            char buf[BUF_SIZE];
            while (body_len > 0) {
                int to_read = (body_len < BUF_SIZE) ? (int)body_len : BUF_SIZE;
                int r = (int)fread(buf, 1, (size_t)to_read, stdin);
                if (r <= 0) break;
                write_all(sock, buf, r);
                body_len -= r;
            }
        }
    }

    /* ---- Read upstream response headers ---- */
    BufReader br;
    br_init(&br, sock);

    char line[BUF_SIZE];
    int  first_line = 1;
    int  is_chunked = 0;
    int  do_rewrite = 0;          /* 1 if response is HTML or CSS */
    int  do_manifest_rewrite = 0; /* 1 if response is a PWA manifest */
    int  saw_content_type = 0;    /* 1 once we forward any Content-Type */

    /* Path-based manifest detection: lighttpd may not send Content-Type
     * for .json files, so detect by URL suffix before reading headers. */
    {
        size_t uplen = strlen(upstream_path);
        const char *suf = "manifest.json";
        size_t slen = strlen(suf);
        if (uplen >= slen &&
            strcmp(upstream_path + uplen - slen, suf) == 0) {
            do_rewrite          = 1;
            do_manifest_rewrite = 1;
        }
    }

    char loc_prefix[80];
    snprintf(loc_prefix, sizeof(loc_prefix), "http://%s:%d", FREETZ_HOST, upstream_port);
    int loc_prefix_len = (int)strlen(loc_prefix);

    while (1) {
        int ll = br_readline(&br, line, BUF_SIZE);
        if (ll < 0) break;

        if (ll == 0) {
            /* End of headers — don't print \r\n yet; we may need to
             * prepend a Content-Length after buffering the body. */
            break;
        }

        if (first_line) {
            first_line = 0;
            char *sp = strchr(line, ' ');
            DBG("  upstream status: [%s]", line);
            printf(sp ? "Status: %s\r\n" : "Status: 200 OK\r\n", sp ? sp+1 : "");
            continue;
        }

        /* Detect whether body needs rewriting */
        if (strncasecmp(line, "Content-Type:", 13) == 0) {
            char *ct = line + 13;
            while (*ct == ' ') ct++;
            saw_content_type = 1;
            if (strncasecmp(ct, "text/html", 9) == 0 ||
                strncasecmp(ct, "text/css",  8) == 0) {
                do_rewrite          = 1;
                do_manifest_rewrite = 0;  /* not a manifest, clear flag */
            }
            if (strncasecmp(ct, "application/manifest+json", 25) == 0) {
                do_rewrite          = 1;  /* buffer the body */
                do_manifest_rewrite = 1;
            }
            DBG("  content-type: [%s] do_rewrite=%d do_manifest=%d",
                ct, do_rewrite, do_manifest_rewrite);
            printf("%s\r\n", line);
            continue;
        }

        /* Suppress Content-Length — we recalculate it when rewriting,
         * and removing it is safe for non-rewritten responses too
         * (HTTP/1.0-style: end of data = end of stream). */
        if (strncasecmp(line, "Content-Length:", 15) == 0) continue;

        /* Transfer-Encoding: chunked — decode transparently */
        if (strncasecmp(line, "Transfer-Encoding:", 18) == 0) {
            if (strstr(line + 18, "chunked")) is_chunked = 1;
            continue;
        }

        /* Rewrite Location header.
         * URL-encode the entire location value so that paths containing
         * '?' and '&' (e.g. /login.cgi?subpage=/&hash=…) survive as a
         * single ?path= parameter value. */
        if (strncasecmp(line, "Location:", 9) == 0) {
            char *loc = line + 9;
            while (*loc == ' ') loc++;

            DBG("  Location raw: [%s]", loc);
            char enc_loc[BUF_SIZE];
            if (strncmp(loc, loc_prefix, (size_t)loc_prefix_len) == 0) {
                /* http://127.0.0.1:PORT/path → extract path */
                const char *path_part = loc + loc_prefix_len;
                if (!path_part[0]) path_part = "/";
                url_path_encode(path_part, enc_loc, (int)sizeof(enc_loc));
            } else if (loc[0] == '/') {
                /* /path — relative path from upstream */
                url_path_encode(loc, enc_loc, (int)sizeof(enc_loc));
            } else if (strncasecmp(loc, "http://",  7) == 0 ||
                       strncasecmp(loc, "https://", 8) == 0) {
                /* Absolute URL — could be http://fritz.box:81/path etc.
                 * Strip the scheme+host+port and extract just the path. */
                const char *p = loc + (strncasecmp(loc, "https://", 8) == 0 ? 8 : 7);
                const char *slash = strchr(p, '/');
                const char *path_part = slash ? slash : "/";
                url_path_encode(path_part, enc_loc, (int)sizeof(enc_loc));
            } else {
                /* Truly external URL (different domain) — forward unchanged */
                DBG("  Location fwd-unchanged: [%s]", loc);
                printf("Location: %s\r\n", loc);
                continue;
            }
            DBG("  Location rewritten: https://%s%s?service=%s&path=%s",
                req_host, script_name, service_name, enc_loc);
            printf("Location: https://%s%s?service=%s&path=%s\r\n",
                   req_host, script_name, service_name, enc_loc);
            continue;
        }

        /* Strip Content-Security-Policy: the AVM websrv sends a strict
         * CSP that blocks CDN scripts/styles legitimately used by Freetz
         * pages (e.g. xterm.js from cdn.jsdelivr.net).  Removing it lets
         * the proxied page behave as it would on plain HTTP. */
        if (strncasecmp(line, "Content-Security-Policy:", 24) == 0) continue;
        if (strncasecmp(line, "Content-Security-Policy-Report-Only:", 36) == 0) continue;

        if (strncasecmp(line, "Set-Cookie:", 11) == 0) {
            DBG("  set-cookie: [%s]", line);
            if (strip_cookies) {
                char stripped_sc[BUF_SIZE];
                strip_cookie_maxage(line, stripped_sc, (int)sizeof(stripped_sc));
                DBG("  set-cookie stripped: [%s]", stripped_sc);
                printf("%s\r\n", stripped_sc);
                continue;
            }
        }
        printf("%s\r\n", line);
    }

    /* ---- Buffer or stream the body ---- */

    /* If the upstream sent no Content-Type but we know it's a manifest,
     * inject the correct MIME type now (before Content-Length). */
    if (do_manifest_rewrite && !saw_content_type)
        printf("Content-Type: application/manifest+json\r\n");

    /* Helper: drain BufReader + socket into g_body_in, return bytes read */
    size_t blen = 0;

    if (do_rewrite) {
        /* Buffer body for rewriting */
        if (is_chunked) {
            char cline[BUF_SIZE];
            while (1) {
                int ll2 = br_readline(&br, cline, BUF_SIZE);
                if (ll2 < 0) break;
                char *semi = strchr(cline, ';'); if (semi) *semi = '\0';
                long csz = strtol(cline, NULL, 16);
                if (csz <= 0) break;
                long rem = csz;
                while (rem > 0) {
                    while (rem > 0 && br.pos < br.len) {
                        if (blen < BODY_IN_MAX) g_body_in[blen++] = br.buf[br.pos];
                        br.pos++; rem--;
                    }
                    if (rem <= 0) break;
                    br.len = (int)read(br.fd, br.buf, BUF_SIZE);
                    if (br.len <= 0) { rem = 0; break; }
                    br.pos = 0;
                }
                br_readline(&br, cline, sizeof(cline)); /* trailing CRLF */
            }
        } else {
            while (br.pos < br.len && blen < BODY_IN_MAX)
                g_body_in[blen++] = br.buf[br.pos++];
            char rbuf[BUF_SIZE]; int r;
            while ((r = (int)read(sock, rbuf, BUF_SIZE)) > 0)
                for (int k = 0; k < r && blen < BODY_IN_MAX; k++)
                    g_body_in[blen++] = rbuf[k];
        }
        g_body_in[blen] = '\0';

        size_t rlen;
        if (do_manifest_rewrite) {
            rlen = rewrite_manifest(g_body_in, blen, script_name, service_name);
            DBG("  body: manifest rewrite in=%zu out=%zu", blen, rlen);
        } else {
            rlen = rewrite_body(g_body_in, blen, service_name, upstream_path, bare_host);
            DBG("  body: html/css rewrite in=%zu out=%zu", blen, rlen);
        }
        printf("Content-Length: %zu\r\n\r\n", rlen);
        fwrite(g_body_out, 1, rlen, stdout);
    } else {
        printf("\r\n");  /* end of headers */
        if (is_chunked) {
            char cline[BUF_SIZE];
            while (1) {
                int ll2 = br_readline(&br, cline, BUF_SIZE);
                if (ll2 < 0) break;
                char *semi = strchr(cline, ';'); if (semi) *semi = '\0';
                long csz = strtol(cline, NULL, 16);
                if (csz <= 0) break;
                long rem = csz;
                while (rem > 0) {
                    while (rem > 0 && br.pos < br.len) {
                        fputc(br.buf[br.pos++], stdout); rem--;
                    }
                    if (rem <= 0) break;
                    br.len = (int)read(br.fd, br.buf, BUF_SIZE);
                    if (br.len <= 0) { rem = 0; break; }
                    br.pos = 0;
                }
                br_readline(&br, cline, sizeof(cline));
            }
        } else {
            if (br.pos < br.len) {
                fwrite(br.buf + br.pos, 1, (size_t)(br.len - br.pos), stdout);
                br.pos = br.len;
            }
            char buf[BUF_SIZE]; int r;
            while ((r = (int)read(sock, buf, BUF_SIZE)) > 0)
                fwrite(buf, 1, (size_t)r, stdout);
        }
    }

    fflush(stdout);
    close(sock);
}

/* ------------------------------------------------------------------
 * Parse a single key=value from a query string.
 * Writes value into out (outsz bytes), URL-decodes it.
 * Returns 1 if found, 0 if not.
 * ------------------------------------------------------------------ */
static int qs_get(const char *qs, const char *key, char *out, int outsz) {
    size_t klen = strlen(key);
    const char *p = qs;
    while (*p) {
        if (strncmp(p, key, klen) == 0 && p[klen] == '=') {
            p += klen + 1;
            int i = 0;
            while (*p && *p != '&' && i < outsz - 1) {
                if (*p == '%' && isxdigit((unsigned char)p[1]) && isxdigit((unsigned char)p[2])) {
                    char hex[3] = { p[1], p[2], 0 };
                    out[i++] = (char)strtol(hex, NULL, 16);
                    p += 3;
                } else if (*p == '+') {
                    out[i++] = ' ';
                    p++;
                } else {
                    out[i++] = *p++;
                }
            }
            out[i] = '\0';
            return 1;
        }
        /* advance to next param */
        while (*p && *p != '&') p++;
        if (*p == '&') p++;
    }
    return 0;
}

/* Build upstream query string: strip proxy-internal params */
static void qs_strip_proxy_params(const char *qs, char *out, int outsz) {
    out[0] = '\0';
    int outlen = 0;
    const char *p = qs;
    while (*p) {
        const char *amp = strchr(p, '&');
        int seglen = amp ? (int)(amp - p) : (int)strlen(p);
        int skip = (strncmp(p, "service=", 8) == 0 ||
                    strncmp(p, "path=",    5) == 0 ||
                    strncmp(p, "_method=", 8) == 0 ||
                    strncmp(p, "_body=",   6) == 0 ||
                    strncmp(p, "_ctype=",  7) == 0);
        if (!skip && outlen + seglen + 2 < outsz) {
            if (outlen > 0) out[outlen++] = '&';
            memcpy(out + outlen, p, (size_t)seglen);
            outlen += seglen;
            out[outlen] = '\0';
        }
        p += seglen;
        if (*p == '&') p++;
    }
}

/* ------------------------------------------------------------------
 * setcfg -- command-line mode: update @key=value directives in config
 *           Usage: freetz_proxy --set @key=val [@key=val ...]
 * Reads the current config, replaces matching @key= lines with the
 * provided values (preserving all other lines), appends new keys that
 * were not found, and writes the result back to the flash config file.
 * Returns 0 on success, 1 on error (message on stderr).
 * ------------------------------------------------------------------ */
#define SETCFG_OUT_MAX 65536
static int setcfg(int nargs, char **args) {
    int i;
    /* Validate: each arg must be "@key=value" */
    for (i = 0; i < nargs; i++) {
        const char *eq = strchr(args[i], '=');
        if (args[i][0] != '@' || !eq) {
            fprintf(stderr, "freetz_proxy --set: invalid arg '%s' (expected @key=value)\n", args[i]);
            return 1;
        }
    }

    /* Locate current config (flash > mod conf > default) */
    static const char * const cfg_candidates[] = {
        "/tmp/flash/mod/freetz-proxy.cfg",
        "/mod/etc/conf/freetz-proxy.cfg",
        "/mod/etc/default.freetz-proxy/freetz-proxy.cfg",
        "/etc/default.freetz-proxy/freetz-proxy.cfg",
        NULL
    };
    FILE *fin = NULL;
    for (i = 0; cfg_candidates[i]; i++) {
        fin = fopen(cfg_candidates[i], "r");
        if (fin) break;
    }

    static char outbuf[SETCFG_OUT_MAX];
    int out_len = 0;
    /* Track which args were matched/replaced in the file */
    int seen[64] = {0};
    int nsafe = (nargs < 64) ? nargs : 64;

    if (fin) {
        char line[512];
        while (fgets(line, (int)sizeof(line), fin)) {
            int replaced = 0;
            if (line[0] == '@') {
                for (i = 0; i < nsafe; i++) {
                    /* length of "@key" part (up to '=') */
                    const char *aeq  = strchr(args[i], '=');
                    int          alen = (int)(aeq - args[i]); /* includes '@' */
                    if (strncmp(line, args[i], (size_t)alen) == 0 && line[alen] == '=') {
                        int wlen = snprintf(outbuf + out_len,
                                           (size_t)(SETCFG_OUT_MAX - out_len - 1),
                                           "%s\n", args[i]);
                        if (wlen > 0 && out_len + wlen < SETCFG_OUT_MAX)
                            out_len += wlen;
                        seen[i] = 1;
                        replaced = 1;
                        break;
                    }
                }
            }
            if (!replaced) {
                size_t ll = strlen(line);
                if (out_len + (int)ll < SETCFG_OUT_MAX) {
                    memcpy(outbuf + out_len, line, ll);
                    out_len += (int)ll;
                }
            }
        }
        fclose(fin);
    }

    /* Append any args that were not present in the original file */
    for (i = 0; i < nsafe; i++) {
        if (!seen[i]) {
            int wlen = snprintf(outbuf + out_len,
                                (size_t)(SETCFG_OUT_MAX - out_len - 1),
                                "%s\n", args[i]);
            if (wlen > 0 && out_len + wlen < SETCFG_OUT_MAX)
                out_len += wlen;
        }
    }

    /* Write to flash config (primary target for persistence) */
    FILE *fout = fopen("/tmp/flash/mod/freetz-proxy.cfg", "w");
    if (!fout) fout = fopen("/mod/etc/conf/freetz-proxy.cfg", "w");
    if (!fout) {
        perror("freetz_proxy --set: cannot write config");
        return 1;
    }
    if (fwrite(outbuf, 1, (size_t)out_len, fout) != (size_t)out_len) {
        perror("freetz_proxy --set: write error");
        fclose(fout);
        return 1;
    }
    fclose(fout);
    return 0;
}

/* ------------------------------------------------------------------
 * main
 * ------------------------------------------------------------------ */
int main(int argc, char **argv) {
    /* Command-line mode: freetz_proxy --set @key=val [@key=val ...] */
    if (argc >= 2 && strcmp(argv[1], "--set") == 0)
        return setcfg(argc - 2, argv + 2);

    /* Normal CGI mode: load config first so dbg_open() can use @trace_file */
    init_internet_patterns();
    load_config();
    ensure_freetz_service();
    dbg_open();

    const char *method       = getenv("REQUEST_METHOD");
    const char *path_info    = getenv("PATH_INFO");
    const char *query_str    = getenv("QUERY_STRING");
    const char *content_len  = getenv("CONTENT_LENGTH");
    const char *content_type = getenv("CONTENT_TYPE");
    const char *script_name  = getenv("SCRIPT_NAME");
    const char *server_name  = getenv("SERVER_NAME");
    const char *http_host    = getenv("HTTP_HOST");

    if (!method)      method      = "GET";
    if (!path_info)   path_info   = "";
    if (!query_str)   query_str   = "";
    if (!script_name) script_name = "/cgi-bin/freetz_proxy";
    if (!server_name) server_name = "fritz.box";

    const char *req_host = http_host ? http_host : server_name;

    /* Method tunnel: when AVM websrv rejects POST from internet it only
     * passes GET requests.  Clients encode the real method in _method=,
     * the URL-encoded body in _body=, and the content-type in _ctype=.
     * Decode them here so do_proxy forwards the right method+body upstream. */
    {
        char _m[16] = "", _ct[128] = "";
        if (qs_get(query_str, "_method", _m, (int)sizeof(_m)) && _m[0]) {
            /* Only allow recognised methods to prevent injection */
            if (strcmp(_m, "POST")   == 0 ||
                strcmp(_m, "PUT")    == 0 ||
                strcmp(_m, "PATCH")  == 0 ||
                strcmp(_m, "DELETE") == 0) {
                /* Use a static buffer for the overridden method name */
                static char _method_buf[16];
                strncpy(_method_buf, _m, sizeof(_method_buf) - 1);
                _method_buf[sizeof(_method_buf) - 1] = '\0';
                method = _method_buf;
                /* Decode body directly into global buffer (avoids large stack alloc) */
                qs_get(query_str, "_body", g_tunnel_body, TUNNEL_BODY_MAX + 1);
                g_tunnel_body_len = (int)strlen(g_tunnel_body);
                snprintf(g_tunnel_clen_str, sizeof(g_tunnel_clen_str),
                         "%d", g_tunnel_body_len);
                content_len = g_tunnel_clen_str;
                /* Content-Type (default to form-encoded if omitted) */
                if (!qs_get(query_str, "_ctype", _ct, (int)sizeof(_ct)) || !_ct[0])
                    strncpy(_ct, "application/x-www-form-urlencoded",
                            sizeof(_ct) - 1);
                strncpy(g_tunnel_ctype_str, _ct, sizeof(g_tunnel_ctype_str) - 1);
                g_tunnel_ctype_str[sizeof(g_tunnel_ctype_str) - 1] = '\0';
                content_type = g_tunnel_ctype_str;
                DBG("  method-tunnel: %s body_len=%d ctype=%s",
                    method, g_tunnel_body_len, content_type);
            }
        }
    }

    DBG(">>> REQUEST: %s QUERY=%s PATH_INFO=%s HOST=%s",
        method, query_str, path_info, req_host ? req_host : "-");
    /* Log all incoming HTTP headers */
    if (g_dbg) {
        extern char **environ;
        for (char **ep = environ; *ep; ep++)
            if (strncmp(*ep, "HTTP_", 5) == 0)
                DBG("  req-hdr: %s", *ep);
    }

    /* Disabled: return a fixed notice page for every request */
    if (g_disabled) {
        printf("Status: 200 OK\r\n"
               "Content-Type: text/html; charset=UTF-8\r\n"
               "\r\n"
               "<!DOCTYPE html>\n<html><head>\n"
               "<meta charset=\"UTF-8\">\n"
               "<title>Freetz Proxy &mdash; Disabled</title>\n"
               "<style>body{font-family:sans-serif;max-width:600px;margin:60px auto;padding:0 16px}"
               "h2{color:#856404}.box{background:#fff3cd;border:1px solid #ffc107;"
               "border-radius:4px;padding:16px 20px}</style>\n"
               "</head><body>\n"
               "<div class=\"box\"><h2>&#x26A0; Freetz Proxy Disabled</h2>\n"
               "<p>The Freetz HTTPS proxy is currently disabled.</p>\n"
               "<p>To re-enable it, uncheck <em>Disable proxy</em> in the proxy settings "
               "under <a href='http://fritz.box:81/cgi-bin/file/mod/freetz_proxy'>"
               "Freetz &rarr; freetz_proxy</a>.</p>\n"
               "</div></body></html>\n");
        fflush(stdout);
        return 0;
    }

    /* Detect internet access: SERVER_NAME matches any configured internet domain pattern */
    g_is_internet = is_internet_host(server_name);

    /* Block proxy from internet if configured */
    if (g_block_internet && g_is_internet) {
        cgi_error(403, "Forbidden", "Proxy access from internet is disabled");
        return 0;
    }

    /*
     * Routing via query string (AVM websrv does not route PATH_INFO sub-paths):
     *   No ?service=   → HTML index page
     *   ?service=name  → proxy to registered port
     *
     * Upstream path comes from ?path=/upstream/path (default "/").
     * All other query params are forwarded to the upstream server.
     *
     * URL examples:
     *   https://fritz.box/cgi-bin/freetz_proxy              → index
     *   https://fritz.box/cgi-bin/freetz_proxy?service=freetz
     *     → proxy http://127.0.0.1:81/
     *   https://fritz.box/cgi-bin/freetz_proxy?service=freetz&path=/cgi-bin/conf/X
     *     → proxy http://127.0.0.1:81/cgi-bin/conf/X
     */
    char service_name[MAX_NAME_LEN] = "";
    qs_get(query_str, "service", service_name, (int)sizeof(service_name));

    if (service_name[0] == '\0') {
        show_index(script_name, req_host);
        return 0;
    }

    /* CDN proxy: fetch an external HTTPS resource via curl and relay it.
     * Used to serve cdn.jsdelivr.net scripts/CSS under 'self' origin so
     * AVM's injected CSP ("script-src 'self'") does not block them. */
    if (strcmp(service_name, "cdn") == 0) {
        char cdn_url[4096] = "";
        qs_get(query_str, "url", cdn_url, (int)sizeof(cdn_url));
        if (cdn_url[0] == '\0') {
            cgi_error(400, "Bad Request", "Missing 'url' parameter");
        } else {
            do_cdn_proxy(cdn_url);
        }
        return 0;
    }

    Service *svc = find_service_full(service_name);
    if (!svc) {
        cgi_error(404, "Not Found", "Unknown service");
        return 0;
    }
    int port = svc->port;

    /* bare_host: hostname without port, used for direct HTTP redirect URLs */
    char bare_host[256];
    strncpy(bare_host, req_host, sizeof(bare_host) - 1);
    bare_host[sizeof(bare_host) - 1] = '\0';
    { char *ch = strchr(bare_host, ':'); if (ch) *ch = '\0'; }

    /* Direct services: 302-redirect to their plain HTTP URL */
    if (svc->direct) {
        /* Use ?path= if provided, else service's configured default path */
        char redir_path[512];
        qs_get(query_str, "path", redir_path, (int)sizeof(redir_path));
        if (redir_path[0] == '\0')
            strncpy(redir_path, svc->path, sizeof(redir_path) - 1);
        redir_path[sizeof(redir_path) - 1] = '\0';

        printf("Status: 302 Found\r\n"
               "Location: http://%s:%d%s\r\n"
               "Content-Type: text/html\r\n"
               "\r\n"
               "<a href=\"http://%s:%d%s\">Redirecting...</a>\n",
               bare_host, port, redir_path,
               bare_host, port, redir_path);
        fflush(stdout);
        return 0;
    }

    /* Upstream path: use ?path= if given, else service's configured default */
    char upstream_path[512] = "";
    qs_get(query_str, "path", upstream_path, (int)sizeof(upstream_path));
    if (upstream_path[0] == '\0')
        strncpy(upstream_path, svc->path, sizeof(upstream_path) - 1);
    upstream_path[sizeof(upstream_path) - 1] = '\0';
    if (upstream_path[0] == '\0') { upstream_path[0] = '/'; upstream_path[1] = '\0'; }

    /* Upstream query string: forward everything except service= and path= */
    char upstream_qs[BUF_SIZE] = "";
    qs_strip_proxy_params(query_str, upstream_qs, (int)sizeof(upstream_qs));

    DBG("  -> do_proxy service=%s port=%d upstream=%s upstream_qs=[%s]",
        service_name, port, upstream_path, upstream_qs);

    do_proxy(port, upstream_path, service_name,
             method, upstream_qs, content_len, content_type,
             script_name, req_host, bare_host);
    return 0;
}
