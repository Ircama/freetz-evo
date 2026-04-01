#!/usr/bin/env python3
"""freetz_translate - Cloud-based translation for freetz-ng build system.

Usage:
  freetz_translate <source_lang> <target_lang> <text> [package_name]
"""

import datetime
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
CACHE_BASE_DIR = SCRIPT_DIR / "translate_cache"

# Memoized cache file parsing to avoid repeated disk JSON parsing in tight loops.
_CACHE_FILE_MEMO = {}


class TranslateError(Exception):
    pass


def load_translate_config() -> None:
    """Load FREETZ_TRANSLATE_* keys from .config when env is missing."""
    base_dir = os.environ.get("FREETZ_BASE_DIR")
    if base_dir:
        config_file = Path(base_dir) / ".config"
    else:
        config_file = SCRIPT_DIR.parent / ".config"

    if not config_file.exists():
        return

    try:
        for line in config_file.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.startswith("FREETZ_TRANSLATE_"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if not key:
                continue

            if os.environ.get(key, ""):
                continue

            value = value.strip()
            if value.startswith('"'):
                value = value[1:]
            if value.endswith('"'):
                value = value[:-1]
            os.environ[key] = value
    except Exception:
        # Keep behavior resilient: if config parse fails, continue with env only.
        return


def die(message: str) -> None:
    print(f"freetz_translate: ERROR: {message}", file=sys.stderr)
    raise TranslateError(message)


def warn(message: str) -> None:
    print(f"freetz_translate: WARNING: {message}", file=sys.stderr)


def debug(message: str) -> None:
    if os.environ.get("FREETZ_TRANSLATE_DEBUG") == "y":
        print(f"freetz_translate: DEBUG: {message}", file=sys.stderr)


def urlencode(string: str) -> str:
    return urllib.parse.quote(string, safe="")


def json_get_string(json_text: str, key: str) -> str:
    try:
        data = json.loads(json_text)
        value = data.get(key, "")
        if value is None:
            return ""
        return str(value)
    except Exception:
        pattern = re.compile(r'"' + re.escape(key) + r'"\s*:\s*"([^"]*)"')
        match = pattern.search(json_text)
        return match.group(1) if match else ""


def json_get_array_first(json_text: str, array_key: str, field_key: str) -> str:
    try:
        data = json.loads(json_text)
        values = data.get(array_key, [])
        if isinstance(values, list) and values:
            first = values[0]
            if isinstance(first, dict):
                value = first.get(field_key, "")
                if value is None:
                    return ""
                return str(value)
        return ""
    except Exception:
        pattern = re.compile(r'"' + re.escape(field_key) + r'"\s*:\s*"([^"]*)"')
        match = pattern.search(json_text)
        return match.group(1) if match else ""


def json_escape(text: str) -> str:
    escaped = text.replace("\\", "\\\\")
    escaped = escaped.replace('"', '\\"')
    escaped = escaped.replace("\n", "\\n")
    escaped = escaped.replace("\r", "\\r")
    escaped = escaped.replace("\t", "\\t")
    return escaped


def json_unescape(text: str) -> str:
    unescaped = text.replace("\\n", "\n")
    unescaped = unescaped.replace("\\r", "")
    unescaped = unescaped.replace("\\t", "\t")
    unescaped = unescaped.replace('\\"', '"')
    unescaped = unescaped.replace("\\\\", "\\")
    return unescaped


def load_deepl_context(lang: str) -> str:
    context_file = CACHE_BASE_DIR / f"{lang}.deepl-context"
    if context_file.exists():
        return context_file.read_text(encoding="utf-8", errors="replace")
    return ""


def cache_key(src: str, tgt: str, text: str, service: str) -> str:
    _ = (src, tgt)
    return f"{service}:{text}"


def _safe_json_load(path: Path):
    path_key = str(path)
    try:
        stat = path.stat()
        token = (stat.st_mtime_ns, stat.st_size)
    except Exception:
        _CACHE_FILE_MEMO[path_key] = (None, None)
        return None

    memo = _CACHE_FILE_MEMO.get(path_key)
    if memo and memo[0] == token:
        return memo[1]

    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
            _CACHE_FILE_MEMO[path_key] = (token, data)
            return data
    except Exception:
        _CACHE_FILE_MEMO[path_key] = (token, None)
        return None


def _cache_search_files(lang: str, package: str = ""):
    files = []
    seen = set()

    if package:
        candidate = CACHE_BASE_DIR / f"{lang}-{package}.json"
        if str(candidate) not in seen:
            files.append(candidate)
            seen.add(str(candidate))

    base_file = CACHE_BASE_DIR / f"{lang}.json"
    if str(base_file) not in seen:
        files.append(base_file)
        seen.add(str(base_file))

    for candidate in sorted(CACHE_BASE_DIR.glob(f"{lang}-*.json")):
        if str(candidate) in seen:
            continue
        files.append(candidate)
        seen.add(str(candidate))

    return files


def cache_get(key: str, lang: str, package: str = ""):
    for cache_file in _cache_search_files(lang, package):
        if not cache_file.exists() or cache_file.suffix != ".json":
            continue
        data = _safe_json_load(cache_file)
        if not isinstance(data, dict):
            continue
        entry = data.get(key, {})
        if isinstance(entry, dict):
            value = entry.get("translation", "")
            if value:
                return str(value)
    return None


def cache_get_original(key: str, lang: str, package: str = ""):
    for cache_file in _cache_search_files(lang, package):
        if not cache_file.exists() or cache_file.suffix != ".json":
            continue
        data = _safe_json_load(cache_file)
        if not isinstance(data, dict):
            continue
        entry = data.get(key, {})
        if isinstance(entry, dict):
            value = entry.get("original", "")
            if value:
                return str(value)
    return None


def cache_get_any_service(src_lang: str, tgt_lang: str, text: str, current_service: str, package: str = ""):
    _ = package
    services = ["deepl", "libretranslate", "apertium", "mymemory", "lingva", "openai"]

    search_files = [CACHE_BASE_DIR / f"{tgt_lang}.json"] + sorted(CACHE_BASE_DIR.glob(f"{tgt_lang}-*.json"))

    for service in services:
        if service == current_service:
            continue
        for cache_file in search_files:
            if not cache_file.exists() or cache_file.suffix != ".json":
                continue
            data = _safe_json_load(cache_file)
            if not isinstance(data, dict):
                continue
            alt_key = cache_key(src_lang, tgt_lang, text, service)
            entry = data.get(alt_key, {})
            if isinstance(entry, dict):
                value = entry.get("translation", "")
                if value:
                    return f"{service}|{value}"
    return None


def _git_user() -> str:
    try:
        import subprocess
    except Exception:
        subprocess = None

    if subprocess is None:
        for env_key in ("GIT_AUTHOR_NAME", "GIT_COMMITTER_NAME", "USER"):
            value = os.environ.get(env_key, "").strip()
            if value:
                return value
        return "unknown"

    try:
        out = subprocess.check_output(
            ["git", "config", "--get", "user.name"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return out if out else "unknown"
    except Exception:
        for env_key in ("GIT_AUTHOR_NAME", "GIT_COMMITTER_NAME", "USER"):
            value = os.environ.get(env_key, "").strip()
            if value:
                return value
        return "unknown"


def cache_put(key: str, original: str, translation: str, lang: str, service: str = "unknown", package: str = "") -> None:
    if package:
        cache_file = CACHE_BASE_DIR / f"{lang}-{package}.json"
    else:
        cache_file = CACHE_BASE_DIR / f"{lang}.json"

    lock_file = Path(str(cache_file) + ".lock")

    CACHE_BASE_DIR.mkdir(parents=True, exist_ok=True)

    lock_timeout = 10
    waited = 0
    while lock_file.exists() and waited < lock_timeout:
        time.sleep(0.1)
        waited += 1

    tmp_file = Path(str(cache_file) + f".tmp.{os.getpid()}")
    try:
        lock_file.touch(exist_ok=True)

        if not cache_file.exists():
            cache_file.write_text("{}\n", encoding="utf-8")

        data = _safe_json_load(cache_file)
        if not isinstance(data, dict):
            print(f"cache_put: jq failed for {cache_file}, skipping save for key: {key}", file=sys.stderr)
            return

        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        github_user = _git_user()

        data[key] = {
            "original": original,
            "translation": translation,
            "timestamp": timestamp,
            "service": service,
            "github_user": github_user,
        }

        with tmp_file.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")

        os.replace(tmp_file, cache_file)
    except Exception:
        print(f"cache_put: jq failed for {cache_file}, skipping save for key: {key}", file=sys.stderr)
        try:
            tmp_file.unlink(missing_ok=True)
        except Exception:
            pass
    finally:
        try:
            lock_file.unlink(missing_ok=True)
        except Exception:
            pass


def deepl_lang_code(lang: str) -> str:
    mapping = {
        "en": "EN",
        "de": "DE",
        "fr": "FR",
        "es": "ES",
        "it": "IT",
        "pt": "PT-PT",
        "nl": "NL",
        "pl": "PL",
        "ru": "RU",
    }
    return mapping.get(lang, lang.upper())


def deepl_source_lang_code(lang: str) -> str:
    mapping = {
        "en": "EN",
        "de": "DE",
        "fr": "FR",
        "es": "ES",
        "it": "IT",
        "pt": "PT",
        "pt-pt": "PT",
        "pt-br": "PT",
        "nl": "NL",
        "pl": "PL",
        "ru": "RU",
    }
    return mapping.get(lang, lang.upper())


def protect_whitespace(text: str) -> str:
    result = text

    lead_match = re.match(r"^\s*", result)
    lead = lead_match.group(0) if lead_match else ""
    if lead:
        lead_spaces = lead.count(" ")
        lead_tabs = lead.count("\t")
        result = result[len(lead):]
        prefix = ""
        if lead_spaces > 0:
            prefix += f"__FREETZ_LEADSP{lead_spaces}__"
        if lead_tabs > 0:
            prefix += f"__FREETZ_LEADTAB{lead_tabs}__"
        result = prefix + result

    trail_match = re.search(r"\s*$", result)
    trail = trail_match.group(0) if trail_match else ""
    if trail:
        trail_spaces = trail.count(" ")
        trail_tabs = trail.count("\t")
        result = result[: len(result) - len(trail)] if trail else result
        if trail_spaces > 0:
            result += f"__FREETZ_TRAILSP{trail_spaces}__"
        if trail_tabs > 0:
            result += f"__FREETZ_TRAILTAB{trail_tabs}__"

    return result


def restore_whitespace(text: str) -> str:
    result = text

    while True:
        match = re.search(r"__FREETZ_LEADSP([0-9]+)__", result)
        if not match:
            break
        count = int(match.group(1))
        result = result.replace(match.group(0), " " * count)

    while True:
        match = re.search(r"__FREETZ_LEADTAB([0-9]+)__", result)
        if not match:
            break
        count = int(match.group(1))
        result = result.replace(match.group(0), "\t" * count)

    while True:
        match = re.search(r"__FREETZ_TRAILSP([0-9]+)__", result)
        if not match:
            break
        count = int(match.group(1))
        result = result.replace(match.group(0), " " * count)

    while True:
        match = re.search(r"__FREETZ_TRAILTAB([0-9]+)__", result)
        if not match:
            break
        count = int(match.group(1))
        result = result.replace(match.group(0), "\t" * count)

    return result


def protect_escape_sequences(text: str) -> str:
    return text.replace("\\n", "__FREETZ_NL__").replace("\\t", "__FREETZ_TAB__").replace("\\r", "__FREETZ_CR__")


def restore_escape_sequences(text: str) -> str:
    return text.replace("__FREETZ_NL__", "\\n").replace("__FREETZ_TAB__", "\\t").replace("__FREETZ_CR__", "\\r")


def protect_shell_commands(text: str) -> str:
    result = text
    counter = 0
    regex = re.compile(r"sed[ \t]+(\"s/[^\"]+\"|'s/[^']+')")

    while True:
        match = regex.search(result)
        if not match:
            break

        matched = match.group(0)
        temp_path = Path(f"/tmp/freetz_protected_cmds_{os.getpid()}_{counter}")
        temp_path.write_text(matched, encoding="utf-8")

        result = result.replace(matched, f"__FREETZ_CMD{counter}__")
        counter += 1
        if counter > 50:
            break

    return result


def restore_shell_commands(text: str) -> str:
    result = text
    counter = 0

    while True:
        temp_path = Path(f"/tmp/freetz_protected_cmds_{os.getpid()}_{counter}")
        if not temp_path.exists():
            break

        cmd = temp_path.read_text(encoding="utf-8", errors="replace").rstrip("\n")
        result = result.replace(f"__FREETZ_CMD{counter}__", cmd)
        temp_path.unlink(missing_ok=True)
        counter += 1

    return result


def _http_request(url: str, method: str = "GET", headers=None, data: bytes = None) -> str:
    request = urllib.request.Request(url=url, data=data, method=method)
    for key, value in (headers or {}).items():
        request.add_header(key, value)

    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def translate_deepl(src_lang: str, tgt_lang: str, text: str) -> str:
    api_key = os.environ.get("FREETZ_TRANSLATE_DEEPL_API_KEY", "")
    if not api_key:
        die("DeepL API key not set (FREETZ_TRANSLATE_DEEPL_API_KEY)")

    stripped_text = text
    trailing_ellipsis = ""
    trailing_spaces = ""
    added_context = False

    match_spaces = re.search(r"\s+$", stripped_text)
    if match_spaces:
        trailing_spaces = match_spaces.group(0)
        stripped_text = stripped_text[: -len(trailing_spaces)]

    match_ellipsis = re.search(r"\.\.\.+$", stripped_text)
    if match_ellipsis:
        trailing_ellipsis = match_ellipsis.group(0)
        stripped_text = stripped_text[: -len(trailing_ellipsis)]

    word_count = len(stripped_text.split())
    text_to_translate = stripped_text
    if word_count <= 2:
        text_to_translate = f"Translate this: {stripped_text}"
        added_context = True

    api_url = "https://api-free.deepl.com/v2/translate"
    if not api_key.endswith(":fx"):
        api_url = "https://api.deepl.com/v2/translate"

    src_code = deepl_source_lang_code(src_lang)
    tgt_code = deepl_lang_code(tgt_lang)
    deepl_context = load_deepl_context(tgt_lang)

    payload = {
        "text": [text_to_translate],
        "source_lang": src_code,
        "target_lang": tgt_code,
        "split_sentences": "0",
    }
    if deepl_context:
        payload["context"] = deepl_context

    try:
        response = _http_request(
            url=api_url,
            method="POST",
            headers={
                "Authorization": f"DeepL-Auth-Key {api_key}",
                "Content-Type": "application/json",
            },
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        )
    except Exception:
        die("DeepL API request failed")

    time.sleep(0.1)

    translated = json_get_array_first(response, "translations", "text")
    if not translated:
        warn(f"DeepL: returned empty translation for: '{text}'")
        raise TranslateError("deepl empty translation")

    translated = json_unescape(translated)

    if added_context:
        match_colon = re.search(r":\s*(.+)$", translated)
        if match_colon:
            translated = match_colon.group(1)
        else:
            match_hint = re.search(r"(Traduci|Tradurre|(?:\u00dc|U)bersetzen|Traducir|Traduire).*:\s*(.+)$", translated)
            if match_hint:
                translated = match_hint.group(2)
            else:
                warn(f"DeepL: could not extract term from context, using full result: '{translated}'")

    return f"{translated}{trailing_ellipsis}{trailing_spaces}"


def translate_libretranslate(src_lang: str, tgt_lang: str, text: str) -> str:
    api_url = os.environ.get("FREETZ_TRANSLATE_API_URL", "https://libretranslate.com").rstrip("/")

    payload = {
        "q": text,
        "source": src_lang,
        "target": tgt_lang,
        "format": "text",
    }

    api_key = os.environ.get("FREETZ_TRANSLATE_LIBRETRANSLATE_API_KEY", "")
    if api_key:
        payload["api_key"] = api_key

    try:
        response = _http_request(
            url=f"{api_url}/translate",
            method="POST",
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        )
    except Exception:
        die("LibreTranslate API request failed")

    translated = json_get_string(response, "translatedText")
    if not translated:
        die(f"LibreTranslate: empty response. API response: {response}")

    return json_unescape(translated)


def translate_apertium(src_lang: str, tgt_lang: str, text: str) -> str:
    api_url = "https://apertium.org/apy/translate"
    query = urllib.parse.urlencode({
        "q": text,
        "langpair": f"{src_lang}|{tgt_lang}",
        "markUnknown": "no",
    })

    try:
        response = _http_request(f"{api_url}?{query}")
    except Exception:
        die("Apertium API request failed")

    translated = ""
    try:
        data = json.loads(response)
        translated = str(data.get("responseData", {}).get("translatedText", ""))
    except Exception:
        translated = ""

    if not translated:
        die(f"Apertium: empty response. API response: {response}")

    return json_unescape(translated)


def translate_mymemory(src_lang: str, tgt_lang: str, text: str) -> str:
    api_url = "https://api.mymemory.translated.net/get"

    text_len = len(text)
    text_trimmed = text.strip()

    if text_trimmed and re.fullmatch(r"[\W\s]+", text_trimmed, flags=re.UNICODE):
        die(f"MyMemory: text is only punctuation/symbols: '{text}'")

    if text_len < 2:
        die(f"MyMemory: text too short ({text_len} chars): '{text}'")
    if text_len == 2:
        if not any(ch.isalpha() for ch in text_trimmed):
            die(f"MyMemory: 2-char text without letters: '{text}'")

    if text_len > 500:
        die(f"MyMemory: text too long ({text_len} chars, max 500). Skipping.")

    params = {
        "q": text,
        "langpair": f"{src_lang}|{tgt_lang}",
    }
    email = os.environ.get("FREETZ_TRANSLATE_MYMEMORY_EMAIL", "")
    if email:
        params["de"] = email

    query = urllib.parse.urlencode(params)
    try:
        response = _http_request(f"{api_url}?{query}")
    except Exception:
        die("MyMemory API request failed")

    translated = ""
    try:
        data = json.loads(response)
        translated = str(data.get("responseData", {}).get("translatedText", ""))
    except Exception:
        translated = ""

    if not translated:
        die(f"MyMemory: empty response. API response: {response}")

    if "QUERY LENGTH LIMIT EXCEEDED" in translated:
        die("MyMemory: query length limit exceeded")
    if "YOU USED ALL AVAILABLE FREE TRANSLATIONS" in translated:
        die("MyMemory: daily quota exceeded. Try again later or provide email.")
    if "MYMEMORY WARNING" in translated:
        die("MyMemory: API warning/error in response")

    translated = json_unescape(translated)

    source_lower = text.lower()
    trans_lower = translated.lower()
    if source_lower == trans_lower:
        warn(f"MyMemory: translation identical to source (may be technical term): '{text}'")

    return translated


def translate_lingva(src_lang: str, tgt_lang: str, text: str) -> str:
    api_url = os.environ.get("FREETZ_TRANSLATE_API_URL", "https://lingva.ml").rstrip("/")
    encoded_text = urlencode(text)

    try:
        response = _http_request(f"{api_url}/api/v1/{src_lang}/{tgt_lang}/{encoded_text}")
    except Exception:
        die("Lingva API request failed")

    translated = json_get_string(response, "translation")
    if not translated:
        die(f"Lingva: empty response. API response: {response}")

    return json_unescape(translated)


def translate_openai(src_lang: str, tgt_lang: str, text: str) -> str:
    api_key = os.environ.get("FREETZ_TRANSLATE_OPENAI_API_KEY", "")
    if not api_key:
        die("OpenAI API key not set (FREETZ_TRANSLATE_OPENAI_API_KEY)")

    tgt_names = {
        "de": "German",
        "en": "English",
        "it": "Italian",
        "fr": "French",
        "es": "Spanish",
        "pt": "Portuguese",
        "nl": "Dutch",
        "pl": "Polish",
        "ru": "Russian",
    }
    src_names = {
        "de": "German",
        "en": "English",
    }

    lang_names = tgt_names.get(tgt_lang, tgt_lang)
    src_lang_name = src_names.get(src_lang, src_lang)

    system_prompt = (
        "You are a translator for a router web interface (Fritz!Box). "
        f"Translate the following {src_lang_name} text to {lang_names}. "
        "Output ONLY the translation, nothing else. Keep it concise and technical. "
        "Preserve any HTML tags, format specifiers, or special characters exactly as they are."
    )

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ],
        "temperature": 0.1,
        "max_tokens": 256,
    }

    try:
        response = _http_request(
            url="https://api.openai.com/v1/chat/completions",
            method="POST",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        )
    except Exception:
        die("OpenAI API request failed")

    translated = ""
    try:
        data = json.loads(response)
        translated = str(data.get("choices", [{}])[0].get("message", {}).get("content", ""))
    except Exception:
        translated = ""

    if not translated:
        die(f"OpenAI: empty response. API response: {response}")

    return json_unescape(translated)


def get_service_name() -> str:
    direct = os.environ.get("FREETZ_TRANSLATE_SERVICE", "")
    if direct:
        return direct

    if os.environ.get("FREETZ_TRANSLATE_DEEPL") == "y":
        return "deepl"
    if os.environ.get("FREETZ_TRANSLATE_LIBRETRANSLATE") == "y":
        return "libretranslate"
    if os.environ.get("FREETZ_TRANSLATE_APERTIUM") == "y":
        return "apertium"
    if os.environ.get("FREETZ_TRANSLATE_MYMEMORY") == "y":
        return "mymemory"
    if os.environ.get("FREETZ_TRANSLATE_LINGVA") == "y":
        return "lingva"
    if os.environ.get("FREETZ_TRANSLATE_OPENAI") == "y":
        return "openai"
    return "none"


def translate(src_lang: str, tgt_lang: str, text: str, package: str = ""):
    if src_lang == tgt_lang:
        return text, 0

    if text == "" or re.sub(r"\s", "", text) == "":
        return text, 0

    service = get_service_name()

    if service == "none":
        warn("No translation service configured, returning source text")
        return text, 1

    debug(f"Using service: {service} (src={src_lang}, tgt={tgt_lang}, package={package})")

    key = ""
    if os.environ.get("FREETZ_TRANSLATE_CACHE_ENABLED") == "y":
        debug("Checking cache...")
        key = cache_key(src_lang, tgt_lang, text, service)
        cached = cache_get(key, tgt_lang, package)
        if cached is not None:
            if package:
                pkg_file = CACHE_BASE_DIR / f"{tgt_lang}-{package}.json"
                already_in_pkg = ""
                data = _safe_json_load(pkg_file)
                if isinstance(data, dict):
                    entry = data.get(key, {})
                    if isinstance(entry, dict):
                        already_in_pkg = str(entry.get("translation", ""))
                if not already_in_pkg:
                    cache_put(key, text, cached, tgt_lang, service, package)
            print("from cache", file=sys.stderr)
            debug(f"Cache HIT: returning cached translation from {service}")
            return cached, 0

        debug(f"Cache MISS: not found in {service} cache")

        if os.environ.get("FREETZ_TRANSLATE_REUSE_CACHE_ANY_SERVICE") == "y":
            debug("Trying alternative service caches...")
            alt_result = cache_get_any_service(src_lang, tgt_lang, text, service, package)
            if alt_result:
                alt_service, alt_translation = alt_result.split("|", 1)
                alt_key = cache_key(src_lang, tgt_lang, text, alt_service)
                if package:
                    cache_put(alt_key, text, alt_translation, tgt_lang, alt_service, package)
                print(f"from cache ({alt_service})", file=sys.stderr)
                debug(f"Cache HIT: reusing translation from alternative service: {alt_service}")
                return alt_translation, 0
            debug("No translation found in any service cache")
    else:
        debug(f"Cache disabled (FREETZ_TRANSLATE_CACHE_ENABLED={os.environ.get('FREETZ_TRANSLATE_CACHE_ENABLED', '')})")

    debug("Applying text protections...")
    protected_text = protect_whitespace(text)
    debug(f"Protected whitespace: '{text}' -> '{protected_text}'")

    protected_text = protect_escape_sequences(protected_text)
    debug("Protected escape sequences")

    protected_text = protect_shell_commands(protected_text)
    debug("Protected shell commands")

    result = ""
    rc = 1

    if service == "deepl":
        debug("Requesting translation from DeepL API...")
        try:
            result = translate_deepl(src_lang, tgt_lang, protected_text)
            rc = 0 if result else 1
        except TranslateError:
            rc = 1
        if rc != 0 or not result:
            warn(f"DeepL failed (rc={rc}), trying MyMemory fallback...")
            debug("Requesting translation from MyMemory API (fallback)...")
            try:
                result = translate_mymemory(src_lang, tgt_lang, protected_text)
                rc = 0 if result else 1
            except TranslateError:
                rc = 1
            if rc == 0 and result:
                debug("Fallback successful: MyMemory returned translation")
            else:
                debug(f"Fallback failed: MyMemory also failed (rc={rc})")
        else:
            debug("DeepL API successful")
    elif service == "libretranslate":
        debug("Requesting translation from LibreTranslate API...")
        try:
            result = translate_libretranslate(src_lang, tgt_lang, protected_text)
            rc = 0 if result else 1
        except TranslateError:
            rc = 1
        debug(f"LibreTranslate API returned: rc={rc}")
    elif service == "apertium":
        debug("Requesting translation from Apertium API...")
        try:
            result = translate_apertium(src_lang, tgt_lang, protected_text)
            rc = 0 if result else 1
        except TranslateError:
            rc = 1
        debug(f"Apertium API returned: rc={rc}")
    elif service == "mymemory":
        debug("Requesting translation from MyMemory API...")
        try:
            result = translate_mymemory(src_lang, tgt_lang, protected_text)
            rc = 0 if result else 1
        except TranslateError:
            rc = 1
        debug(f"MyMemory API returned: rc={rc}")
    elif service == "lingva":
        debug("Requesting translation from Lingva API...")
        try:
            result = translate_lingva(src_lang, tgt_lang, protected_text)
            rc = 0 if result else 1
        except TranslateError:
            rc = 1
        debug(f"Lingva API returned: rc={rc}")
    elif service == "openai":
        debug("Requesting translation from OpenAI API...")
        try:
            result = translate_openai(src_lang, tgt_lang, protected_text)
            rc = 0 if result else 1
        except TranslateError:
            rc = 1
        debug(f"OpenAI API returned: rc={rc}")
    else:
        die(f"Unknown translation service: {service}")

    if rc != 0 or not result:
        warn(f"Translation failed for: {text}")
        debug(f"Final result: FAILED (rc={rc}, result='{result}')")
        return text, 1

    debug(f"Translation successful: '{protected_text}' -> '{result}'")

    debug("Restoring text protections...")
    result = restore_shell_commands(result)
    debug("Restored shell commands")
    result = restore_escape_sequences(result)
    debug("Restored escape sequences")
    result = restore_whitespace(result)
    debug(f"Restored whitespace: final result='{result}'")

    if os.environ.get("FREETZ_TRANSLATE_CACHE_ENABLED") == "y":
        debug(f"Caching translation: service={service}, lang={tgt_lang}")
        cache_put(key, text, result, tgt_lang, service, package)
    else:
        debug(f"Not caching (FREETZ_TRANSLATE_CACHE_ENABLED={os.environ.get('FREETZ_TRANSLATE_CACHE_ENABLED', '')})")

    return result, 0


def usage(program_name: str) -> None:
    print(f"Usage: {program_name} <source_lang> <target_lang> <text> [package_name]", file=sys.stderr)
    print("  Translates <text> from <source_lang> to <target_lang>", file=sys.stderr)
    print("  using the configured translation service.", file=sys.stderr)
    print("  Optional package_name for package-specific cache.", file=sys.stderr)
    print("", file=sys.stderr)
    print("  Configure via environment variables:", file=sys.stderr)
    print("    FREETZ_TRANSLATE_DEEPL=y  (+ FREETZ_TRANSLATE_DEEPL_API_KEY)", file=sys.stderr)
    print(
        "    FREETZ_TRANSLATE_LIBRETRANSLATE=y  (+ FREETZ_TRANSLATE_LIBRETRANSLATE_API_KEY, optional FREETZ_TRANSLATE_API_URL)",
        file=sys.stderr,
    )
    print("    FREETZ_TRANSLATE_APERTIUM=y", file=sys.stderr)
    print("    FREETZ_TRANSLATE_MYMEMORY=y  (+ optional FREETZ_TRANSLATE_MYMEMORY_EMAIL)", file=sys.stderr)
    print("    FREETZ_TRANSLATE_LINGVA=y  (+ optional FREETZ_TRANSLATE_API_URL)", file=sys.stderr)
    print("    FREETZ_TRANSLATE_OPENAI=y  (+ FREETZ_TRANSLATE_OPENAI_API_KEY)", file=sys.stderr)


def main(argv=None) -> int:
    load_translate_config()

    args = list(sys.argv if argv is None else argv)
    if len(args) < 4:
        prog = os.environ.get("FREETZ_TRANSLATE_PROGNAME", args[0] if args else "freetz_translate")
        usage(prog)
        return 1

    src_lang = args[1]
    tgt_lang = args[2]
    text = args[3]
    package = args[4] if len(args) > 4 else ""

    try:
        result, rc = translate(src_lang, tgt_lang, text, package)
    except KeyboardInterrupt:
        return 130
    except TranslateError:
        return 1

    sys.stdout.write(result)
    return rc


if __name__ == "__main__":
    sys.exit(main())
