#!/bin/sh
#exec 2>/tmp/ncdu-cgi-error.log

DAEMON=ncdu
. /etc/init.d/modlibrc

if [ -r /usr/lib/libmodcgi.sh ]; then
  . /usr/lib/libmodcgi.sh
elif [ -r /mod/usr/lib/libmodcgi.sh ]; then
  . /mod/usr/lib/libmodcgi.sh
else
  printf 'Content-Type: text/plain\n\nMissing libmodcgi.sh (expected in /usr/lib or /mod/usr/lib)\n'
  exit 1
fi

# Load saved configuration
[ -r /mod/etc/conf/ncdu.cfg ] && . /mod/etc/conf/ncdu.cfg
DEFAULT_SCAN_DIR="${NCDU_SCAN_DIR:-/var/media/ftp}"
[ -n "$DEFAULT_SCAN_DIR" ] || DEFAULT_SCAN_DIR="/var/media/ftp"
NCDU_BIN="$(command -v ncdu 2>/dev/null)"
LOG_FILE='/tmp/ncdu-cgi.log'
LAST_SCAN_FILE='/tmp/ncdu-cgi-last-scan.json'

json_escape() {
  printf '%s' "$1" | sed ':a;N;$!ba;s/\\/\\\\/g;s/"/\\"/g;s/\t/\\t/g;s/\r/\\r/g;s/\n/\\n/g'
}

emit_json_error() {
  _err="$(json_escape "$1")"
  printf '{"success":false,"error":"%s"}' "$_err"
}

emit_json_ok() {
  _msg="$(json_escape "$1")"
  printf '{"success":true,"message":"%s"}' "$_msg"
}

append_log() {
  printf '%s [ncdu-cgi] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$1" >> "$LOG_FILE" 2>/dev/null
}

is_path_syntax_safe() {
  _p="$1"
  [ -n "$_p" ] || return 1
  case "$_p" in
    /*) ;;
    *) return 1 ;;
  esac
  case "$_p" in
    *../*|*/../*|../*|*/..|*".."*) return 1 ;;
  esac
  return 0
}

is_allowed_prefix() {
  _p="$1"
  case "$_p" in
    /var/media/ftp*|/var/media*|/var/mod*|/tmp*|/var/tmp*|/mod*) return 0 ;;
    *) return 1 ;;
  esac
}

normalize_existing_path() {
  readlink -f -- "$1" 2>/dev/null
}

emit_quick_paths() {
  _first=1
  printf '{"success":true,"paths":['
  for _d in /var/media/ftp /var/media /var/mod /tmp /var/tmp /mod; do
    [ -d "$_d" ] || continue
    [ "$_first" = "1" ] || printf ','
    printf '"%s"' "$_d"
    _first=0
  done
  for _d in /var/media/ftp/*; do
    [ -d "$_d" ] || continue
    [ "$_first" = "1" ] || printf ','
    printf '"%s"' "$_d"
    _first=0
  done
  printf ']}'
}

AJAX_MODE=$(cgi_param ajax)

if [ "$AJAX_MODE" = "1" ]; then
  ACTION=$(cgi_param action)

  printf 'Content-Type: text/html; charset=UTF-8\n\n'
  printf '<style>\n.ajax-json-box { display: none; }\n</style>\n'
  printf '<div class="ajax-json-box"><div class="ajax-json-content"><pre>Content-Type: application/json\n\n'

  case "$ACTION" in
    scan)
      SCAN_PATH=$(cgi_param path)
      FOLLOW_SYMLINKS=$(cgi_param follow_symlinks)
      ONE_FS=$(cgi_param one_fs)
      DEBUG_LOG=$(cgi_param debug_log)
      [ -n "$SCAN_PATH" ] || SCAN_PATH="$DEFAULT_SCAN_DIR"

      [ "$DEBUG_LOG" = "1" ] && append_log "scan start path='$SCAN_PATH' follow_symlinks=${FOLLOW_SYMLINKS:-0} one_fs=${ONE_FS:-0}"

      if [ -z "$NCDU_BIN" ]; then
        [ "$DEBUG_LOG" = "1" ] && append_log 'scan error: ncdu binary not found'
        emit_json_error "ncdu binary not found"
      elif ! is_path_syntax_safe "$SCAN_PATH"; then
        [ "$DEBUG_LOG" = "1" ] && append_log "scan error: invalid path '$SCAN_PATH'"
        emit_json_error "Invalid scan path"
      elif [ ! -d "$SCAN_PATH" ]; then
        [ "$DEBUG_LOG" = "1" ] && append_log "scan error: directory does not exist '$SCAN_PATH'"
        emit_json_error "Directory does not exist"
      else
        REAL_SCAN="$(normalize_existing_path "$SCAN_PATH")"
        if [ -z "$REAL_SCAN" ] || ! is_allowed_prefix "$REAL_SCAN"; then
          [ "$DEBUG_LOG" = "1" ] && append_log "scan error: path not allowed '$REAL_SCAN'"
          emit_json_error "Path not allowed"
        else
          OUT_FILE="/tmp/ncdu-scan.$$.json"
          ERR_FILE="/tmp/ncdu-scan.$$.err"
          NCDU_ARGS='-0 --exclude-kernfs --exclude-caches -e -o-'
          [ "$FOLLOW_SYMLINKS" = "1" ] && NCDU_ARGS="$NCDU_ARGS -L"
          [ "$ONE_FS" = "1" ] && NCDU_ARGS="$NCDU_ARGS -x"

          # shellcheck disable=SC2086
          if "$NCDU_BIN" $NCDU_ARGS -- "$REAL_SCAN" >"$OUT_FILE" 2>"$ERR_FILE"; then
            if [ "$DEBUG_LOG" = "1" ]; then
              OUT_BYTES="$(wc -c < "$OUT_FILE" 2>/dev/null)"
              OUT_BYTES="${OUT_BYTES:-0}"
              cp "$OUT_FILE" "$LAST_SCAN_FILE" 2>/dev/null
              append_log "scan ok path='$REAL_SCAN' args='$NCDU_ARGS' bytes=$OUT_BYTES"
              if [ -s "$ERR_FILE" ]; then
                ERR_SHORT="$(head -n 3 "$ERR_FILE" 2>/dev/null | tr '\n' ' ')"
                [ -n "$ERR_SHORT" ] && append_log "scan stderr: $ERR_SHORT"
              fi
            fi
            cat "$OUT_FILE"
          else
            ERR_TEXT="$(head -n 20 "$ERR_FILE" 2>/dev/null)"
            [ -n "$ERR_TEXT" ] || ERR_TEXT="ncdu scan failed"
            if [ "$DEBUG_LOG" = "1" ]; then
              ERR_SHORT="$(printf '%s' "$ERR_TEXT" | head -c 400 | tr '\n' ' ')"
              append_log "scan failed path='$REAL_SCAN' args='$NCDU_ARGS' err='$ERR_SHORT'"
            fi
            emit_json_error "$ERR_TEXT"
          fi
          rm -f "$OUT_FILE" "$ERR_FILE"
        fi
      fi
      ;;

    list_paths)
      emit_quick_paths
      ;;

    read_log)
      LOG_TXT=''
      LOG_META=''
      if [ -r "$LOG_FILE" ]; then
        LOG_TXT="$(tail -n 200 "$LOG_FILE" 2>/dev/null)"
      fi
      if [ -r "$LAST_SCAN_FILE" ]; then
        LAST_BYTES="$(wc -c < "$LAST_SCAN_FILE" 2>/dev/null)"
        LOG_META="Last scan dump: $LAST_SCAN_FILE (${LAST_BYTES:-0} bytes)"
      fi
      printf '{"success":true,"log":"%s","meta":"%s"}' "$(json_escape "$LOG_TXT")" "$(json_escape "$LOG_META")"
      ;;

    clear_log)
      : > "$LOG_FILE" 2>/dev/null
      rm -f "$LAST_SCAN_FILE"
      emit_json_ok 'Debug log cleared'
      ;;

    delete_entry)
      TARGET=$(cgi_param target)
      SCAN_ROOT=$(cgi_param scan_root)
      if ! is_path_syntax_safe "$TARGET" || ! is_path_syntax_safe "$SCAN_ROOT"; then
        emit_json_error "Invalid path"
      elif [ ! -e "$TARGET" ]; then
        emit_json_error "Path does not exist"
      else
        REAL_TARGET="$(normalize_existing_path "$TARGET")"
        REAL_ROOT="$(normalize_existing_path "$SCAN_ROOT")"
        if [ -z "$REAL_TARGET" ] || [ -z "$REAL_ROOT" ]; then
          emit_json_error "Unable to resolve paths"
        elif ! is_allowed_prefix "$REAL_TARGET" || ! is_allowed_prefix "$REAL_ROOT"; then
          emit_json_error "Path not allowed"
        elif [ "$REAL_TARGET" = "/" ] || [ "$REAL_TARGET" = "$REAL_ROOT" ]; then
          emit_json_error "Refusing to delete scan root"
        else
          case "$REAL_TARGET" in
            "$REAL_ROOT"/*)
              if [ -d "$REAL_TARGET" ]; then
                rm -rf -- "$REAL_TARGET"
              else
                rm -f -- "$REAL_TARGET"
              fi
              if [ $? -eq 0 ]; then
                emit_json_ok "Deleted: $REAL_TARGET"
              else
                emit_json_error "Delete failed"
              fi
              ;;
            *)
              emit_json_error "Target is outside scan root"
              ;;
          esac
        fi
      fi
      ;;

    *)
      emit_json_error "Unknown action"
      ;;
  esac

  printf '\n</pre></div></div>\n'
  exit 0
fi

sec_begin "Disk usage (ncdu)" "ncduSection"

printf '<input type="hidden" id="ncdu-default-path" value="%s" />\n' "$DEFAULT_SCAN_DIR"

cat <<'EOF'
<style>
#ncdu-toolbar {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
  margin: 10px 0;
}
#ncdu-toolbar input[type="text"] {
  min-width: 280px;
  flex: 1 1 360px;
  padding: 5px 8px;
  border: 1px solid #bbb;
  border-radius: 3px;
}
#ncdu-options {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin: 8px 0;
}
#ncdu-details-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
  margin: 8px 0;
}
#ncdu-sort-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
  margin: 8px 0;
}
#ncdu-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin: 8px 0;
}
#ncdu-paths {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin: 6px 0 10px 0;
}
.ncdu-path-chip {
  padding: 3px 9px;
  border: 1px solid #aeb6bf;
  border-radius: 12px;
  background: #f7f8f9;
  cursor: pointer;
  font-size: 12px;
}
.ncdu-path-chip:hover {
  background: #e8f0f8;
}
#ncdu-status {
  min-height: 22px;
  margin-top: 4px;
  font-size: 13px;
  color: #39414a;
}
#ncdu-status.error {
  color: #9d1e1e;
}
#ncdu-tree {
  margin-top: 10px;
  border-top: 1px solid #d7dce2;
  padding-top: 8px;
  font-family: monospace;
  font-size: 13px;
  line-height: 1.45;
  overflow-x: auto;
}
.ncdu-row {
  display: flex;
  align-items: center;
  flex-wrap: nowrap;
  gap: 6px;
  padding: 2px 4px;
  border-radius: 3px;
  min-width: max-content;
  user-select: none;
}
.ncdu-row:hover {
  background: #eef3f9;
}
.ncdu-row.selected {
  background: #124b92 !important;
  color: #ffffff !important;
  outline: 1px solid #0c3668;
}
.ncdu-row.selected .ncdu-bar-wrap {
  background: #0d3a70;
  border-color: #5f96cf;
}
.ncdu-row.selected .ncdu-bar {
  background: linear-gradient(90deg, #9dc3e4 0%, #d2e6f7 100%) !important;
}
.ncdu-row.selected .ncdu-toggle,
.ncdu-row.selected .ncdu-size,
.ncdu-row.selected .ncdu-pct,
.ncdu-row.selected .ncdu-name,
.ncdu-row.selected .ncdu-name.dir,
.ncdu-row.selected .ncdu-meta {
  color: #ffffff !important;
}
.ncdu-toggle {
  width: 36px;
  text-align: center;
  color: #6a7581;
  flex-shrink: 0;
  font-size: 22px;
  line-height: 1;
}
.ncdu-size {
  width: 88px;
  text-align: right;
  color: #3f4b58;
  flex-shrink: 0;
}
.ncdu-bar-wrap {
  display: inline-block;
  width: 140px;
  height: 10px;
  border-radius: 2px;
  background: #d6dde7;
  border: 1px solid #b3c0cf;
  overflow: hidden;
  flex-shrink: 0;
}
.ncdu-bar {
  display: block;
  height: 10px;
  border-radius: 2px;
  background: linear-gradient(90deg, #165ea8 0%, #3f8dd8 100%) !important;
}
.ncdu-pct {
  width: 60px;
  text-align: right;
  color: #4b5663;
  flex-shrink: 0;
}
.ncdu-name {
  word-break: normal;
  white-space: nowrap;
  color: #1f2b37;
}
.ncdu-name.dir {
  color: #124b92;
  font-weight: 600;
}
.ncdu-meta {
  margin-left: 8px;
  white-space: normal;
  overflow: hidden;
}
.ncdu-meta-table {
  border-collapse: collapse;
  border-spacing: 0;
  table-layout: fixed;
}
.ncdu-meta-table td {
  padding: 0 10px 0 0;
  white-space: nowrap;
  color: #5d6875;
  font-size: 12px;
  vertical-align: baseline;
}
.ncdu-meta-table td::before {
  content: attr(data-key) ': ';
  color: #4f5b68;
  font-size: 11px;
  font-weight: 600;
}
.ncdu-meta-col-type { width: 112px; }
.ncdu-meta-col-size { width: 172px; }
.ncdu-meta-col-uid { width: 96px; }
.ncdu-meta-col-gid { width: 96px; }
.ncdu-meta-col-mode { width: 184px; }
.ncdu-meta-col-mtime { width: 248px; }
.ncdu-meta-col-dev { width: 118px; }
.ncdu-meta-col-ino { width: 132px; }
.ncdu-meta-col-nlink { width: 118px; }
.ncdu-meta-col-notreg { width: 120px; }
.ncdu-row.selected .ncdu-meta-table td,
.ncdu-row.selected .ncdu-meta-table td::before {
  color: #ffffff !important;
}
.ncdu-flat-wrap {
  overflow-x: auto;
}
.ncdu-flat-table {
  border-collapse: collapse;
  border-spacing: 0;
  table-layout: fixed;
  width: max-content;
  min-width: 100%;
}
.ncdu-flat-table th,
.ncdu-flat-table td {
  padding: 2px 6px;
  border-bottom: 1px solid #e3e8ee;
  white-space: nowrap;
  vertical-align: middle;
}
.ncdu-flat-table th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: #f3f7fb;
  color: #314356;
  font-weight: 600;
  font-size: 12px;
  text-align: left;
}
.ncdu-flat-table tr.ncdu-row {
  display: table-row;
  align-items: initial;
  flex-wrap: nowrap;
  gap: 0;
  padding: 0;
  border-radius: 0;
  min-width: 0;
}
.ncdu-flat-table .ncdu-flat-col-toggle { width: 40px; text-align: center; }
.ncdu-flat-table .ncdu-flat-col-bar { width: 150px; }
.ncdu-flat-table .ncdu-flat-col-pct { width: 64px; text-align: right; }
.ncdu-flat-table .ncdu-flat-col-size { width: 94px; text-align: right; }
.ncdu-flat-table .ncdu-flat-col-name { width: 520px; max-width: 520px; }
.ncdu-flat-table td.ncdu-flat-col-name {
  overflow: hidden;
  text-overflow: ellipsis;
}
.ncdu-flat-table td.ncdu-flat-col-name .ncdu-name {
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  vertical-align: bottom;
}
.ncdu-flat-table td.ncdu-flat-meta {
  color: #5d6875;
  font-size: 12px;
}
.ncdu-flat-table tr.ncdu-row:hover td {
  background: #eef3f9;
}
.ncdu-flat-table tr.ncdu-row.selected td {
  background: #124b92 !important;
  color: #ffffff !important;
  outline: none;
}
.ncdu-flat-table tr.ncdu-row.selected .ncdu-name,
.ncdu-flat-table tr.ncdu-row.selected .ncdu-name.dir,
.ncdu-flat-table tr.ncdu-row.selected .ncdu-pct,
.ncdu-flat-table tr.ncdu-row.selected .ncdu-size,
.ncdu-flat-table tr.ncdu-row.selected .ncdu-flat-meta {
  color: #ffffff !important;
}
.ncdu-flat-table tr.ncdu-row.selected .ncdu-bar-wrap {
  background: #0d3a70;
  border-color: #5f96cf;
}
.ncdu-flat-table tr.ncdu-row.selected .ncdu-bar {
  background: linear-gradient(90deg, #9dc3e4 0%, #d2e6f7 100%) !important;
}
.ncdu-children {
  padding-left: 16px;
}
.ncdu-hidden {
  display: none;
}
#ncdu-context-menu {
  position: fixed;
  z-index: 10000;
  min-width: 190px;
  background: #ffffff !important;
  color: #1b1f23 !important;
  border: 1px solid #b8c2cc;
  border-radius: 4px;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.18);
  padding: 4px;
}
#ncdu-context-menu button {
  display: block;
  width: 100%;
  text-align: left;
  background: #fff !important;
  color: #1b1f23 !important;
  border: 0;
  border-radius: 3px;
  padding: 6px 8px;
  font-size: 12px;
  cursor: pointer;
}
#ncdu-context-menu button:hover {
  background: #6fa8dc !important;
  color: #001b38 !important;
}
#ncdu-context-menu button:disabled {
  color: #9aa4af;
  cursor: default;
}
#ncdu-summary {
  font-size: 13px;
  color: #4b5663;
  margin-bottom: 8px;
}
#ncdu-log-panel {
  margin-top: 10px;
  border: 1px solid #d7dce2;
  border-radius: 4px;
  background: #f9fbfd;
  padding: 8px;
}
#ncdu-log-meta {
  margin: 0 0 6px 0;
  font-size: 12px;
  color: #4b5663;
}
#ncdu-log {
  margin: 0;
  max-height: 240px;
  overflow: auto;
  white-space: pre-wrap;
  font-family: monospace;
  font-size: 12px;
  line-height: 1.4;
}
#ncdu-busy {
  position: fixed;
  right: 10px;
  top: 10px;
  z-index: 10001;
  padding: 6px 10px;
  border-radius: 14px;
  background: rgba(16, 48, 88, 0.9);
  color: #ffffff;
  font-size: 12px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.25);
}
/* Hide framework form buttons (Apply/Default) on this custom AJAX page. */
input[type="submit"],
input[type="reset"],
button[type="submit"] {
  display: none !important;
}
</style>

<div id="ncdu-toolbar">
  <input type="text" id="ncdu-path" />
  <button type="button" id="ncdu-scan">Scan</button>
  <button type="button" id="ncdu-rescan">Rescan</button>
</div>

<div id="ncdu-options">
  <label><input type="checkbox" id="ncdu-follow"> Follow symlinks</label>
  <label><input type="checkbox" id="ncdu-onefs"> Stay on one filesystem</label>
  <label><input type="checkbox" id="ncdu-showhidden"> Show hidden</label>
  <label><input type="checkbox" id="ncdu-flatview"> Flat view (all objects)</label>
  <label><input type="checkbox" id="ncdu-debuglog"> Debug log</label>
</div>

<div id="ncdu-details-row">
  <label>Details:</label>
  <select id="ncdu-meta-mode">
    <option value="off">Off</option>
    <option value="compact">Compact</option>
    <option value="full">Full</option>
  </select>
</div>

<div id="ncdu-sort-row">
  <label>Sort by:
    <select id="ncdu-sort">
      <option value="dsize" selected>Disk size (dsize)</option>
      <option value="asize">Apparent size (asize)</option>
      <option value="uid">Owner user ID (uid)</option>
      <option value="gid">Owner group ID (gid)</option>
      <option value="mtime">Last modified (mtime)</option>
    </select>
  </label>
  <button type="button" id="ncdu-order">Descending</button>
</div>

<div id="ncdu-actions">
  <button type="button" id="ncdu-open-selected">Open selected directory</button>
  <button type="button" id="ncdu-expand-all">Expand all</button>
  <button type="button" id="ncdu-collapse-all">Collapse all</button>
  <button type="button" id="ncdu-delete">Delete selected</button>
  <button type="button" id="ncdu-show-log">Show log</button>
  <button type="button" id="ncdu-clear-log">Clear log</button>
</div>

<div id="ncdu-paths"></div>
<div id="ncdu-status"></div>
<div id="ncdu-tree"></div>
<div id="ncdu-busy" class="ncdu-hidden">⌛ Working...</div>
<div id="ncdu-log-panel" class="ncdu-hidden">
  <div id="ncdu-log-meta"></div>
  <pre id="ncdu-log"></pre>
</div>
<div id="ncdu-context-menu" class="ncdu-hidden">
  <button type="button" id="ncdu-ctx-open">Open selected directory</button>
  <button type="button" id="ncdu-ctx-toggle">Expand/Collapse</button>
  <button type="button" id="ncdu-ctx-delete">Delete selected</button>
  <button type="button" id="ncdu-ctx-copy">Copy path</button>
</div>

<script>
(function () {
  window.paceOptions = {
    startOnPageLoad: false,
    ajax: false,
    document: false,
    eventLag: false,
    elements: false,
    restartOnPushState: false,
    restartOnRequestAfter: false
  };

  var API_URL = '/cgi-bin/conf/ncdu';
  var state = {
    root: null,
    scanRoot: '',
    selectedPath: '',
    sortKey: 'dsize',
    sortDesc: true,
    showHidden: false,
    flatView: false,
    metaMode: 'off',
    barMax: 1,
    lastPath: ''
  };
  var busyCount = 0;

  var defaultPath = '/var/media/ftp';
  var defaultPathEl = document.getElementById('ncdu-default-path');
  if (defaultPathEl && defaultPathEl.value) defaultPath = defaultPathEl.value;

  function setStatus(msg, isError) {
    var el = document.getElementById('ncdu-status');
    el.textContent = msg || '';
    el.className = isError ? 'error' : '';
  }

  function fmtSize(bytes) {
    var n = Number(bytes) || 0;
    if (n <= 0) return '0 B';
    var units = ['B', 'KiB', 'MiB', 'GiB', 'TiB'];
    var i = 0;
    while (n >= 1024 && i < units.length - 1) {
      n /= 1024;
      i++;
    }
    return (i === 0 ? Math.round(n) : n.toFixed(1)) + ' ' + units[i];
  }

  function fmtPct(pct) {
    var v = Number(pct) || 0;
    if (v <= 0) return '0%';
    if (v >= 10) return v.toFixed(1) + '%';
    if (v >= 1) return v.toFixed(2) + '%';
    return v.toFixed(3) + '%';
  }

  function modeToPerm(modeVal) {
    if (modeVal === undefined || modeVal === null || modeVal === '') return '';
    var m = Number(modeVal);
    if (!isFinite(m)) return '';
    var p = ['-', '-', '-', '-', '-', '-', '-', '-', '-'];
    if (m & 256) p[0] = 'r';
    if (m & 128) p[1] = 'w';
    if (m & 64) p[2] = 'x';
    if (m & 32) p[3] = 'r';
    if (m & 16) p[4] = 'w';
    if (m & 8) p[5] = 'x';
    if (m & 4) p[6] = 'r';
    if (m & 2) p[7] = 'w';
    if (m & 1) p[8] = 'x';
    if (m & 2048) p[2] = (p[2] === 'x') ? 's' : 'S';
    if (m & 1024) p[5] = (p[5] === 'x') ? 's' : 'S';
    if (m & 512) p[8] = (p[8] === 'x') ? 't' : 'T';
    return p.join('');
  }

  function fmtMtime(epochVal) {
    var n = Number(epochVal);
    if (!isFinite(n) || n <= 0) return String(epochVal || '');
    var d = new Date(n * 1000);
    if (!isFinite(d.getTime())) return String(epochVal || '');
    return d.toLocaleString();
  }

  function busyStart(msg) {
    busyCount++;
    var el = document.getElementById('ncdu-busy');
    if (el) {
      el.textContent = '⌛ ' + (msg || 'Working...');
      el.classList.remove('ncdu-hidden');
    }
    if (window.Pace) {
      try { Pace.stop(); } catch (e) {}
      try { Pace.bar.render(); } catch (e) {}
    }
  }

  function busyStop() {
    busyCount = Math.max(0, busyCount - 1);
    if (busyCount > 0) return;
    var el = document.getElementById('ncdu-busy');
    if (el) el.classList.add('ncdu-hidden');
    if (window.Pace) {
      try { Pace.stop(); } catch (e) {}
    }
  }

  function hasVal(v) {
    return !(v === undefined || v === null || v === '');
  }

  function metaParts(node, includePath) {
    var meta = node.meta || {};
    var parts = [];
    if (includePath) parts.push('path=' + node.path);
    parts.push('type=' + (node.isDir ? 'dir' : 'file'));
    parts.push('size=' + fmtSize(nodeSize(node)));
    if (hasVal(meta.uid)) parts.push('uid=' + meta.uid);
    if (hasVal(meta.gid)) parts.push('gid=' + meta.gid);
    if (hasVal(meta.mode)) parts.push('mode=' + modeToPerm(meta.mode));
    if (hasVal(meta.mtime)) parts.push('mtime=' + fmtMtime(meta.mtime));
    if (hasVal(meta.dev)) parts.push('dev=' + meta.dev);
    if (hasVal(meta.ino)) parts.push('ino=' + meta.ino);
    if (hasVal(meta.nlink)) parts.push('nlink=' + meta.nlink);
    if (meta.notreg === true) parts.push('notreg=true');
    return parts;
  }

  function metaTooltip(node) {
    return metaParts(node, true).join('\n');
  }

  function metaFieldValue(node, key) {
    var meta = node.meta || {};
    if (key === 'type') return node.isDir ? 'dir' : 'file';
    if (key === 'size') return fmtSize(nodeSize(node));
    if (key === 'uid') return hasVal(meta.uid) ? String(meta.uid) : '-';
    if (key === 'gid') return hasVal(meta.gid) ? String(meta.gid) : '-';
    if (key === 'mode') return hasVal(meta.mode) ? modeToPerm(meta.mode) : '-';
    if (key === 'mtime') return hasVal(meta.mtime) ? fmtMtime(meta.mtime) : '-';
    if (key === 'dev') return hasVal(meta.dev) ? String(meta.dev) : '-';
    if (key === 'ino') return hasVal(meta.ino) ? String(meta.ino) : '-';
    if (key === 'nlink') return hasVal(meta.nlink) ? String(meta.nlink) : '-';
    if (key === 'notreg') return meta.notreg === true ? 'true' : 'false';
    return '-';
  }

  function metaFieldList() {
    if (state.metaMode === 'compact') {
      return ['type', 'size', 'uid', 'gid', 'mtime'];
    }
    return ['type', 'size', 'uid', 'gid', 'mode', 'mtime', 'dev', 'ino', 'nlink', 'notreg'];
  }

  function renderMetaTable(node) {
    var table = document.createElement('table');
    table.className = 'ncdu-meta-table';
    var colgroup = document.createElement('colgroup');
    table.appendChild(colgroup);

    var tbody = document.createElement('tbody');
    var row = document.createElement('tr');
    tbody.appendChild(row);
    table.appendChild(tbody);

    var fields = metaFieldList();
    for (var i = 0; i < fields.length; i++) {
      var k = fields[i];
      var col = document.createElement('col');
      col.className = 'ncdu-meta-col ncdu-meta-col-' + k;
      colgroup.appendChild(col);

      var td = document.createElement('td');
      td.className = 'ncdu-meta-td ncdu-meta-td-' + k;
      td.setAttribute('data-key', k);
      td.textContent = metaFieldValue(node, k);
      row.appendChild(td);
    }
    return table;
  }

  function markerPayload(text) {
    var marker = 'Content-Type: application/json';
    var pos = text.indexOf(marker);
    if (pos < 0) throw new Error('Invalid CGI response');

    var src = text.slice(pos + marker.length);
    var preEnd = src.indexOf('</pre>');
    if (preEnd >= 0) src = src.slice(0, preEnd);
    src = src.trim();
    if (!src) throw new Error('Empty JSON payload');

    /* Robust extractor: parse first complete JSON object/array and ignore wrapper tail. */
    var start = src.search(/[\[{]/);
    if (start < 0) throw new Error('JSON payload not found');

    var stack = [];
    var inString = false;
    var escaped = false;
    for (var i = start; i < src.length; i++) {
      var ch = src[i];
      if (inString) {
        if (escaped) {
          escaped = false;
        } else if (ch === '\\') {
          escaped = true;
        } else if (ch === '"') {
          inString = false;
        }
        continue;
      }
      if (ch === '"') {
        inString = true;
        continue;
      }

      if (ch === '{' || ch === '[') {
        stack.push(ch);
        continue;
      }

      if (ch === '}' || ch === ']') {
        if (!stack.length) continue;
        var last = stack[stack.length - 1];
        if ((last === '{' && ch === '}') || (last === '[' && ch === ']')) {
          stack.pop();
        }
        if (stack.length === 0) {
          return JSON.parse(src.slice(start, i + 1));
        }
      }
    }

    throw new Error('Incomplete JSON payload');
  }

  function callApi(action, params) {
    var q = new URLSearchParams();
    q.set('ajax', '1');
    q.set('action', action);
    Object.keys(params || {}).forEach(function (k) {
      if (params[k] !== undefined && params[k] !== null) {
        q.set(k, String(params[k]));
      }
    });
    return fetch(API_URL + '?' + q.toString())
      .then(function (r) { return r.text(); })
      .then(markerPayload);
  }

  function debugEnabled() {
    var el = document.getElementById('ncdu-debuglog');
    return (el && el.checked) ? 1 : 0;
  }

  function setLogContent(text, meta) {
    var panel = document.getElementById('ncdu-log-panel');
    var logEl = document.getElementById('ncdu-log');
    var metaEl = document.getElementById('ncdu-log-meta');
    panel.classList.remove('ncdu-hidden');
    metaEl.textContent = meta || '';
    logEl.textContent = text || '(empty log)';
  }

  function showDebugLog() {
    busyStart('Loading debug log...');
    callApi('read_log', {}).then(function (res) {
      if (!res || res.success !== true) {
        setStatus((res && res.error) ? res.error : 'Unable to read debug log.', true);
        busyStop();
        return;
      }
      setLogContent(res.log || '', res.meta || '');
      setStatus('Debug log loaded.');
      busyStop();
    }).catch(function (err) {
      setStatus('Unable to read debug log: ' + err.message, true);
      busyStop();
    });
  }

  function clearDebugLog() {
    busyStart('Clearing debug log...');
    callApi('clear_log', {}).then(function (res) {
      if (!res || res.success !== true) {
        setStatus((res && res.error) ? res.error : 'Unable to clear debug log.', true);
        busyStop();
        return;
      }
      setLogContent('', '');
      setStatus(res.message || 'Debug log cleared.');
      busyStop();
    }).catch(function (err) {
      setStatus('Unable to clear debug log: ' + err.message, true);
      busyStop();
    });
  }

  function nodeSize(node) {
    var d = Number(node.dsize);
    if (isFinite(d) && d >= 0) return d;
    var a = Number(node.asize);
    if (isFinite(a) && a >= 0) return a;
    return 0;
  }

  function toNumOrNull(v) {
    if (!hasVal(v)) return null;
    var n = Number(v);
    return isFinite(n) ? n : null;
  }

  function joinPath(parent, name) {
    if (!name || name === '.') return parent;
    if (parent === '/') return '/' + name;
    return parent.replace(/\/$/, '') + '/' + name;
  }

  function basename(path) {
    if (!path) return '/';
    if (path === '/') return '/';
    return path.replace(/\/$/, '').split('/').pop() || '/';
  }

  function entryToNode(entry, parentPath, isRoot) {
    if (Array.isArray(entry)) {
      var meta = entry[0] || {};
      var dirPath = isRoot ? parentPath : joinPath(parentPath, meta.name || '');
      var dirNode = {
        name: isRoot ? basename(dirPath) : (meta.name || '?'),
        path: dirPath,
        asize: toNumOrNull(meta.asize),
        dsize: toNumOrNull(meta.dsize),
        items: meta.items || 0,
        isDir: true,
        expanded: !!isRoot,
        meta: {
          uid: meta.uid,
          gid: meta.gid,
          mode: meta.mode,
          mtime: meta.mtime,
          dev: meta.dev,
          ino: meta.ino,
          nlink: meta.nlink,
          notreg: meta.notreg === true
        },
        children: [],
        parent: null
      };
      for (var i = 1; i < entry.length; i++) {
        var child = entryToNode(entry[i], dirPath, false);
        if (child) {
          child.parent = dirNode;
          dirNode.children.push(child);
        }
      }
      if (!dirNode.items) dirNode.items = dirNode.children.length;
      return dirNode;
    }

    if (!entry || typeof entry !== 'object') return null;
    return {
      name: entry.name || '?',
      path: joinPath(parentPath, entry.name || ''),
      asize: toNumOrNull(entry.asize),
      dsize: toNumOrNull(entry.dsize),
      items: 0,
      isDir: false,
      expanded: false,
      meta: {
        uid: entry.uid,
        gid: entry.gid,
        mode: entry.mode,
        mtime: entry.mtime,
        dev: entry.dev,
        ino: entry.ino,
        nlink: entry.nlink,
        notreg: entry.notreg === true
      },
      children: [],
      parent: null
    };
  }

  function parseNcduPayload(payload, fallbackPath) {
    if (!Array.isArray(payload) || payload.length < 4) {
      throw new Error('Unexpected ncdu payload');
    }
    var header = payload[2] || {};
    var rootEntry = payload[3];
    var rootMeta = (Array.isArray(rootEntry) && rootEntry.length && rootEntry[0] && typeof rootEntry[0] === 'object') ? rootEntry[0] : {};
    var rootMetaName = String(rootMeta.name || '');
    var rootPath = header.path || ((rootMetaName.charAt(0) === '/') ? rootMetaName : '') || fallbackPath || '/';
    var rootNode = entryToNode(rootEntry, rootPath, true);
    if (!rootNode) throw new Error('Unable to parse ncdu tree');
    rootNode.name = basename(rootPath);
    rootNode.path = rootPath;
    rootNode.expanded = true;
    return rootNode;
  }

  function cmp(a, b) {
    if (a < b) return -1;
    if (a > b) return 1;
    return 0;
  }

  function sortMetric(node) {
    var key = state.sortKey;
    var meta = node.meta || {};
    if (key === 'dsize') {
      return (toNumOrNull(node.dsize) !== null) ? Number(node.dsize) : ((toNumOrNull(node.asize) !== null) ? Number(node.asize) : 0);
    }
    if (key === 'uid') return Number(meta.uid || 0);
    if (key === 'gid') return Number(meta.gid || 0);
    if (key === 'mtime') return Number(meta.mtime || 0);
    if (key === 'asize') {
      return (toNumOrNull(node.asize) !== null) ? Number(node.asize) : ((toNumOrNull(node.dsize) !== null) ? Number(node.dsize) : 0);
    }
    return nodeSize(node);
  }

  function sortLabel() {
    if (state.sortKey === 'dsize') return 'dsize';
    if (state.sortKey === 'asize') return 'asize';
    if (state.sortKey === 'uid') return 'uid';
    if (state.sortKey === 'gid') return 'gid';
    if (state.sortKey === 'mtime') return 'mtime';
    return state.sortKey;
  }

  function cmpNatural(a, b) {
    return String(a || '').localeCompare(String(b || ''), undefined, {
      numeric: true,
      sensitivity: 'base'
    });
  }

  function sortNodeList(arr) {
    arr.sort(function (a, b) {
      if (a.isDir !== b.isDir && !state.flatView) return a.isDir ? -1 : 1;
      var cMetric = cmp(sortMetric(a), sortMetric(b));
      if (cMetric !== 0) return state.sortDesc ? -cMetric : cMetric;

      /* Deterministic tiebreakers keep flat view globally sorted even when metrics match. */
      var cPath = cmpNatural(a.path, b.path);
      if (cPath !== 0) return cPath;

      var cName = cmpNatural(a.name, b.name);
      return cName;
    });
    return arr;
  }

  function sortedVisibleChildren(node) {
    var arr = (node.children || []).filter(function (n) {
      if (!state.showHidden && n.name && n.name.charAt(0) === '.') return false;
      return true;
    });
    return sortNodeList(arr);
  }

  function renderTree() {
    var root = state.root;
    var container = document.getElementById('ncdu-tree');
    container.innerHTML = '';
    if (!root) return;

    var summary = document.createElement('div');
    summary.id = 'ncdu-summary';
    summary.textContent = root.path + ' | Total: ' + fmtSize(nodeSize(root)) + (state.flatView ? ' | Flat view' : ' | Tree view') + ' | Sort: ' + sortLabel() + ' ' + (state.sortDesc ? 'desc' : 'asc');
    container.appendChild(summary);

    var wrapper = document.createElement('div');
    wrapper.className = 'ncdu-children';
    container.appendChild(wrapper);

    if (state.flatView) {
      renderFlatTable(root, wrapper);
      return;
    }

    state.barMax = Math.max(1, computeTreeBarMax(root));
    renderNode(root, wrapper, true);
  }

  function computeTreeBarMax(root) {
    var maxv = 0;
    function visit(node) {
      if (!node) return;
      if (node !== root) {
        maxv = Math.max(maxv, nodeSize(node));
      }
      if (!node.isDir || !node.expanded) return;
      var children = sortedVisibleChildren(node);
      for (var i = 0; i < children.length; i++) visit(children[i]);
    }
    visit(root);
    if (maxv <= 0) maxv = nodeSize(root);
    return maxv;
  }

  function renderFlatTable(root, wrapper) {
    var arr = [];
    walk(root, function (n) {
      if (n === root) return;
      if (!state.showHidden && n.name && n.name.charAt(0) === '.') return;
      arr.push(n);
    });
    sortNodeList(arr);
    state.barMax = Math.max(1, arr.reduce(function (m, n) {
      return Math.max(m, nodeSize(n));
    }, 0));

    var flatWrap = document.createElement('div');
    flatWrap.className = 'ncdu-flat-wrap';
    var table = document.createElement('table');
    table.className = 'ncdu-flat-table';
    flatWrap.appendChild(table);

    var colgroup = document.createElement('colgroup');
    table.appendChild(colgroup);
    function appendCol(cls) {
      var col = document.createElement('col');
      col.className = cls;
      colgroup.appendChild(col);
    }
    appendCol('ncdu-flat-col-toggle');
    appendCol('ncdu-flat-col-bar');
    appendCol('ncdu-flat-col-pct');
    appendCol('ncdu-flat-col-size');
    appendCol('ncdu-flat-col-name');

    var fields = state.metaMode !== 'off' ? metaFieldList() : [];
    for (var ci = 0; ci < fields.length; ci++) {
      appendCol('ncdu-meta-col-' + fields[ci]);
    }

    var thead = document.createElement('thead');
    var hr = document.createElement('tr');
    var headers = [
      { label: '', cls: 'ncdu-flat-col-toggle' },
      { label: 'Usage', cls: 'ncdu-flat-col-bar' },
      { label: '%', cls: 'ncdu-flat-col-pct' },
      { label: 'Size', cls: 'ncdu-flat-col-size' },
      { label: 'Name', cls: 'ncdu-flat-col-name' }
    ];
    for (var h = 0; h < headers.length; h++) {
      var th = document.createElement('th');
      th.className = headers[h].cls;
      th.textContent = headers[h].label;
      hr.appendChild(th);
    }
    for (var fi = 0; fi < fields.length; fi++) {
      var fth = document.createElement('th');
      fth.className = 'ncdu-meta-col-' + fields[fi];
      fth.textContent = fields[fi];
      hr.appendChild(fth);
    }
    thead.appendChild(hr);
    table.appendChild(thead);

    var tbody = document.createElement('tbody');
    table.appendChild(tbody);

    for (var i = 0; i < arr.length; i++) {
      var node = arr[i];
      var tr = document.createElement('tr');
      tr.className = 'ncdu-row' + (state.selectedPath === node.path ? ' selected' : '');
      tr.dataset.path = node.path;
      tr.title = metaTooltip(node);

      var toggleTd = document.createElement('td');
      toggleTd.className = 'ncdu-flat-col-toggle';
      var toggle = document.createElement('span');
      toggle.className = 'ncdu-toggle';
      toggle.textContent = node.isDir ? '◦' : '•';
      toggleTd.appendChild(toggle);
      tr.appendChild(toggleTd);

      var size = nodeSize(node);
      var refSize = Math.max(1, Number(state.barMax || 1));
      var pct = (size / refSize) * 100;
      var barWidth = size > 0 ? Math.max(1, Math.min(100, pct)) : 0;

      var barTd = document.createElement('td');
      barTd.className = 'ncdu-flat-col-bar';
      var barWrap = document.createElement('span');
      barWrap.className = 'ncdu-bar-wrap';
      var bar = document.createElement('span');
      bar.className = 'ncdu-bar';
      bar.style.width = barWidth + '%';
      barWrap.appendChild(bar);
      barTd.appendChild(barWrap);
      tr.appendChild(barTd);

      var pctTd = document.createElement('td');
      pctTd.className = 'ncdu-flat-col-pct ncdu-pct';
      pctTd.textContent = fmtPct(pct);
      tr.appendChild(pctTd);

      var sizeTd = document.createElement('td');
      sizeTd.className = 'ncdu-flat-col-size ncdu-size';
      sizeTd.textContent = fmtSize(size);
      tr.appendChild(sizeTd);

      var nameTd = document.createElement('td');
      nameTd.className = 'ncdu-flat-col-name';
      var nameEl = document.createElement('span');
      nameEl.className = 'ncdu-name' + (node.isDir ? ' dir' : '');
      nameEl.textContent = node.name || '/';
      nameTd.appendChild(nameEl);
      tr.appendChild(nameTd);

      for (var mf = 0; mf < fields.length; mf++) {
        var mk = fields[mf];
        var md = document.createElement('td');
        md.className = 'ncdu-flat-meta ncdu-meta-col-' + mk;
        md.textContent = metaFieldValue(node, mk);
        tr.appendChild(md);
      }

      tr.addEventListener('click', function (ev) {
        ev.stopPropagation();
        hideContextMenu();
        state.selectedPath = this.dataset.path;
        renderTree();
      });

      tr.addEventListener('contextmenu', function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        hideContextMenu();
        state.selectedPath = this.dataset.path;
        renderTree();
        showContextMenu(ev.clientX, ev.clientY);
      });

      tbody.appendChild(tr);
    }

    wrapper.appendChild(flatWrap);
  }

  function renderNode(node, parentEl, isRoot) {
    var row = document.createElement('div');
    row.className = 'ncdu-row' + (state.selectedPath === node.path ? ' selected' : '');
    row.dataset.path = node.path;

    var toggle = document.createElement('span');
    toggle.className = 'ncdu-toggle';
    var hasChildren = node.isDir && !state.flatView && node.children && node.children.length > 0;
    if (node.isDir) {
      toggle.textContent = hasChildren ? (node.expanded ? '▾' : '▸') : '◦';
    } else {
      toggle.textContent = '•';
    }
    row.appendChild(toggle);

    var size = nodeSize(node);
    var refSize = Math.max(1, Number(state.barMax || 1));
    var pct = (size / refSize) * 100;
    var barWidth = size > 0 ? Math.max(1, Math.min(100, pct)) : 0;

    var barWrap = document.createElement('span');
    barWrap.className = 'ncdu-bar-wrap';
    var bar = document.createElement('span');
    bar.className = 'ncdu-bar';
    bar.style.width = barWidth + '%';
    barWrap.appendChild(bar);
    row.appendChild(barWrap);

    var pctEl = document.createElement('span');
    pctEl.className = 'ncdu-pct';
    pctEl.textContent = fmtPct(pct);
    row.appendChild(pctEl);

    var sizeEl = document.createElement('span');
    sizeEl.className = 'ncdu-size';
    sizeEl.textContent = fmtSize(size);
    row.appendChild(sizeEl);

    var nameEl = document.createElement('span');
    nameEl.className = 'ncdu-name' + (node.isDir ? ' dir' : '');
    nameEl.textContent = node.name || '/';
    row.appendChild(nameEl);

    if (state.metaMode !== 'off') {
      var metaEl = document.createElement('div');
      metaEl.className = 'ncdu-meta';
      metaEl.appendChild(renderMetaTable(node));
      row.appendChild(metaEl);
    }

    row.title = metaTooltip(node);

    row.addEventListener('click', function (ev) {
      ev.stopPropagation();
      hideContextMenu();
      state.selectedPath = node.path;
      renderTree();
    });

    row.addEventListener('contextmenu', function (ev) {
      ev.preventDefault();
      ev.stopPropagation();
      state.selectedPath = node.path;
      renderTree();
      showContextMenu(ev.clientX, ev.clientY);
    });

    if (node.isDir) {
      row.addEventListener('dblclick', function (ev) {
        ev.stopPropagation();
        hideContextMenu();
        if (!hasChildren) return;
        node.expanded = !node.expanded;
        renderTree();
      });
      toggle.addEventListener('click', function (ev) {
        ev.stopPropagation();
        hideContextMenu();
        if (!hasChildren) return;
        node.expanded = !node.expanded;
        renderTree();
      });
    }

    parentEl.appendChild(row);

    if (node.isDir && node.expanded && hasChildren) {
      var children = sortedVisibleChildren(node);
      var childWrap = document.createElement('div');
      childWrap.className = 'ncdu-children';
      children.forEach(function (child) {
        renderNode(child, childWrap, false);
      });
      parentEl.appendChild(childWrap);
    }
  }

  function hideContextMenu() {
    document.getElementById('ncdu-context-menu').classList.add('ncdu-hidden');
  }

  function showContextMenu(x, y) {
    var menu = document.getElementById('ncdu-context-menu');
    var node = findNodeByPath(state.root, state.selectedPath);
    var openBtn = document.getElementById('ncdu-ctx-open');
    var toggleBtn = document.getElementById('ncdu-ctx-toggle');
    var delBtn = document.getElementById('ncdu-ctx-delete');

    if (!node) {
      hideContextMenu();
      return;
    }

    var hasChildren = node.isDir && !state.flatView && node.children && node.children.length > 0;
    openBtn.disabled = !node.isDir;
    toggleBtn.disabled = !hasChildren;
    toggleBtn.textContent = hasChildren ? (node.expanded ? 'Collapse selected' : 'Expand selected') : 'Empty directory';
    delBtn.disabled = (node.path === state.scanRoot);

    menu.classList.remove('ncdu-hidden');
    menu.style.left = '0px';
    menu.style.top = '0px';

    var mw = menu.offsetWidth;
    var mh = menu.offsetHeight;
    var left = x;
    var top = y;

    if (left + mw > window.innerWidth - 4) left = Math.max(4, window.innerWidth - mw - 4);
    if (top + mh > window.innerHeight - 4) top = Math.max(4, window.innerHeight - mh - 4);

    menu.style.left = left + 'px';
    menu.style.top = top + 'px';
  }

  function copyTextRobust(text) {
    if (!text) return Promise.reject(new Error('Empty text'));
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text).catch(function () {
        return new Promise(function (resolve, reject) {
          var ta = document.createElement('textarea');
          ta.value = text;
          ta.setAttribute('readonly', 'readonly');
          ta.style.position = 'fixed';
          ta.style.left = '-9999px';
          ta.style.top = '0';
          document.body.appendChild(ta);
          ta.focus();
          ta.select();
          try {
            if (document.execCommand('copy')) resolve();
            else reject(new Error('copy command failed'));
          } catch (e) {
            reject(e);
          } finally {
            document.body.removeChild(ta);
          }
        });
      });
    }
    return new Promise(function (resolve, reject) {
      var ta = document.createElement('textarea');
      ta.value = text;
      ta.setAttribute('readonly', 'readonly');
      ta.style.position = 'fixed';
      ta.style.left = '-9999px';
      ta.style.top = '0';
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      try {
        if (document.execCommand('copy')) resolve();
        else reject(new Error('copy command failed'));
      } catch (e) {
        reject(e);
      } finally {
        document.body.removeChild(ta);
      }
    });
  }

  function findNodeByPath(node, path) {
    if (!node) return null;
    if (node.path === path) return node;
    for (var i = 0; i < node.children.length; i++) {
      var found = findNodeByPath(node.children[i], path);
      if (found) return found;
    }
    return null;
  }

  function walk(node, fn) {
    if (!node) return;
    fn(node);
    node.children.forEach(function (c) { walk(c, fn); });
  }

  function removeNode(target) {
    if (!target || !target.parent) return;
    target.parent.children = target.parent.children.filter(function (c) {
      return c !== target;
    });
  }

  function scanCurrent() {
    var scanBtn = document.getElementById('ncdu-scan');
    var path = document.getElementById('ncdu-path').value.trim();
    if (!path) {
      setStatus('Please enter a path.', true);
      return;
    }

    scanBtn.disabled = true;
    document.getElementById('ncdu-rescan').disabled = true;
    busyStart('Scanning...');
    setStatus('Scanning...');

    callApi('scan', {
      path: path,
      follow_symlinks: document.getElementById('ncdu-follow').checked ? 1 : 0,
      one_fs: document.getElementById('ncdu-onefs').checked ? 1 : 0,
      debug_log: debugEnabled()
    }).then(function (data) {
      scanBtn.disabled = false;
      document.getElementById('ncdu-rescan').disabled = false;
      if (!Array.isArray(data)) {
        setStatus((data && data.error) ? data.error : 'Scan failed.', true);
        if (debugEnabled()) showDebugLog();
        busyStop();
        return;
      }
      state.root = parseNcduPayload(data, path);
      state.scanRoot = state.root.path;
      state.selectedPath = state.root.path;
      state.lastPath = path;
      setStatus('Scan complete.');
      if (debugEnabled()) showDebugLog();
      renderTree();
      busyStop();
    }).catch(function (err) {
      scanBtn.disabled = false;
      document.getElementById('ncdu-rescan').disabled = false;
      setStatus('Scan failed: ' + err.message, true);
      if (debugEnabled()) showDebugLog();
      busyStop();
    });
  }

  function toggleOrder() {
    state.sortDesc = !state.sortDesc;
    document.getElementById('ncdu-order').textContent = state.sortDesc ? 'Descending' : 'Ascending';
    renderTree();
  }

  function expandAll(openState) {
    walk(state.root, function (n) {
      if (n.isDir) n.expanded = openState;
    });
    renderTree();
  }

  function openSelectedDirectory() {
    var node = findNodeByPath(state.root, state.selectedPath);
    if (!node) {
      setStatus('No selected entry.', true);
      return;
    }
    if (!node.isDir) node = node.parent;
    if (!node || !node.path) {
      setStatus('No directory selected.', true);
      return;
    }
    document.getElementById('ncdu-path').value = node.path;
    scanCurrent();
  }

  function deleteSelected() {
    var node = findNodeByPath(state.root, state.selectedPath);
    if (!node) {
      setStatus('No selected entry.', true);
      return;
    }
    if (node.path === state.scanRoot) {
      setStatus('Refusing to delete scan root.', true);
      return;
    }
    if (!confirm('Delete ' + node.path + ' ?')) return;

    callApi('delete_entry', {
      target: node.path,
      scan_root: state.scanRoot
    }).then(function (res) {
      if (!res || res.success !== true) {
        setStatus((res && res.error) ? res.error : 'Delete failed.', true);
        return;
      }
      removeNode(node);
      state.selectedPath = state.scanRoot;
      setStatus(res.message || 'Deleted.');
      renderTree();
    }).catch(function (err) {
      setStatus('Delete failed: ' + err.message, true);
    });
  }

  function initQuickPaths() {
    callApi('list_paths', {}).then(function (res) {
      if (!res || res.success !== true || !Array.isArray(res.paths)) return;
      var host = document.getElementById('ncdu-paths');
      host.innerHTML = '';
      res.paths.forEach(function (p) {
        var chip = document.createElement('span');
        chip.className = 'ncdu-path-chip';
        chip.textContent = p;
        chip.addEventListener('click', function () {
          document.getElementById('ncdu-path').value = p;
        });
        host.appendChild(chip);
      });
    }).catch(function () {
      /* Ignore quick path errors */
    });
  }

  document.getElementById('ncdu-path').value = defaultPath;
  var sortSelInit = document.getElementById('ncdu-sort');
  if (sortSelInit && sortSelInit.value) state.sortKey = sortSelInit.value;
  document.getElementById('ncdu-path').addEventListener('keydown', function (ev) {
    if (ev.key === 'Enter') {
      ev.preventDefault();
      ev.stopPropagation();
      scanCurrent();
    }
  });
  document.getElementById('ncdu-path').addEventListener('keypress', function (ev) {
    if (ev.key === 'Enter') {
      ev.preventDefault();
      ev.stopPropagation();
      scanCurrent();
    }
  });
  document.addEventListener('submit', function (ev) {
    var pathEl = document.getElementById('ncdu-path');
    if (!pathEl) return;
    var active = document.activeElement;
    var isPathActive = (active === pathEl);
    var formContainsPath = !!(ev.target && ev.target.contains && ev.target.contains(pathEl));
    if (!isPathActive && !formContainsPath) return;
    ev.preventDefault();
    ev.stopPropagation();
    scanCurrent();
  }, true);
  document.getElementById('ncdu-scan').addEventListener('click', scanCurrent);
  document.getElementById('ncdu-rescan').addEventListener('click', function () {
    if (state.lastPath) document.getElementById('ncdu-path').value = state.lastPath;
    scanCurrent();
  });
  document.getElementById('ncdu-order').addEventListener('click', toggleOrder);
  document.getElementById('ncdu-sort').addEventListener('change', function (ev) {
    state.sortKey = ev.target.value || 'asize';
    renderTree();
  });
  document.getElementById('ncdu-showhidden').addEventListener('change', function (ev) {
    state.showHidden = !!ev.target.checked;
    renderTree();
  });
  document.getElementById('ncdu-flatview').addEventListener('change', function (ev) {
    busyStart('Building view...');
    window.setTimeout(function () {
      state.flatView = !!ev.target.checked;
      renderTree();
      setStatus(state.flatView ? 'Flat view ready.' : 'Tree view ready.');
      busyStop();
    }, 0);
  });
  document.getElementById('ncdu-meta-mode').addEventListener('change', function (ev) {
    state.metaMode = ev.target.value || 'off';
    renderTree();
  });
  document.getElementById('ncdu-expand-all').addEventListener('click', function () { expandAll(true); });
  document.getElementById('ncdu-collapse-all').addEventListener('click', function () { expandAll(false); });
  document.getElementById('ncdu-open-selected').addEventListener('click', openSelectedDirectory);
  document.getElementById('ncdu-delete').addEventListener('click', deleteSelected);
  document.getElementById('ncdu-show-log').addEventListener('click', showDebugLog);
  document.getElementById('ncdu-clear-log').addEventListener('click', clearDebugLog);

  document.getElementById('ncdu-ctx-open').addEventListener('click', function () {
    hideContextMenu();
    openSelectedDirectory();
  });
  document.getElementById('ncdu-ctx-toggle').addEventListener('click', function () {
    hideContextMenu();
    var node = findNodeByPath(state.root, state.selectedPath);
    if (node && node.isDir) {
      node.expanded = !node.expanded;
      renderTree();
    }
  });
  document.getElementById('ncdu-ctx-delete').addEventListener('click', function () {
    hideContextMenu();
    deleteSelected();
  });
  document.getElementById('ncdu-ctx-copy').addEventListener('click', function () {
    hideContextMenu();
    if (!state.selectedPath) return;
    copyTextRobust(state.selectedPath).then(function () {
      setStatus('Copied: ' + state.selectedPath);
    }).catch(function () {
      setStatus('Copy failed, path in input box.');
      document.getElementById('ncdu-path').value = state.selectedPath;
      window.prompt('Copy path manually:', state.selectedPath);
    });
  });

  document.addEventListener('click', function () {
    hideContextMenu();
  });
  document.addEventListener('scroll', function () {
    hideContextMenu();
  }, true);
  document.addEventListener('keydown', function (ev) {
    if (ev.key === 'Escape') hideContextMenu();
  });

  initQuickPaths();
})();
</script>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/pace-js@1.2.4/themes/blue/pace-theme-center-radar.css">
<script src="https://cdn.jsdelivr.net/npm/pace-js@1.2.4/pace.min.js"></script>
EOF

sec_end
