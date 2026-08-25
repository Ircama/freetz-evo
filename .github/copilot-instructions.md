# Freetz-ng Package Development Guide

This document contains comprehensive guidelines, patterns, and best practices for developing packages in freetz-ng, extracted from real-world development experience.

## Prime Directive: Work Like freetz-ng, Not Like a Generic Web App

**CRITICAL UNDERSTANDING**: freetz-ng is NOT a traditional web application framework. It uses a specialized configuration pipeline that must be understood and followed:

### The modconf Framework

- **Variables must be exported**: If a variable isn't `export`ed in `/mod/etc/default.<pkg>/<pkg>.cfg`, `modconf` won't discover it → it won't be saved.
- **Framework orchestrates saves**: The web "Save" flow is managed by framework code (`save_body.sh`), not directly by your CGI.
- **Hook timing is critical**: `pkg_pre_save()` runs BEFORE save, `pkg_apply_save()` runs AFTER. Updating runtime configs in the wrong hook = stale values.
- **POST data is consumed**: Don't try to read POST parameters in save hooks; the framework has already processed them into environment variables.

### Common Architecture Failures (Prevent These)

1. **Variable Not Exported** → modconf doesn't list it → form field ignored → value never saved
2. **Update in pkg_pre_save()** → reads old cfg → runtime file gets stale values
3. **Direct POST parsing in hooks** → returns empty → validation fails mysteriously  
4. **Implicit restart on save** → unexpected service interruption → bad UX

### Key Distinction: System Variables vs Runtime Pass-Through

- **System variables**: Used by init scripts (`ENABLED`, `BASEDIR`, `NICE`)
- **Runtime pass-through**: Captured from form, written to application config files (e.g., `.rc`), NOT used by init scripts

Both must be exported in default cfg for framework capture, but document their different purposes.

---

## Table of Contents

1. [Package Structure](#package-structure)
2. [Configuration Framework (modconf)](#configuration-framework)
3. [CGI Script Development](#cgi-script-development)
4. [Web Interface Editors](#web-interface-editors)
5. [Init Scripts (rc.*)](#init-scripts)
6. [Template System](#template-system)
7. [Deployment Scripts](#deployment-scripts)
8. [Common Pitfalls](#common-pitfalls)
9. [Best Practices](#best-practices)
10. [Debug Playbook](#debug-playbook)

---

## Package Structure

### Directory Layout

```
make/pkgs/[package-name]/
├── Config.in                    # Package configuration options
├── [package-name].mk            # Makefile for package
└── files/
    ├── .language                # Language file marker
    └── root/                    # Mirrors target filesystem
        ├── etc/
        │   ├── init.d/
        │   │   └── rc.[package]       # Init script
        │   └── default.[package]/
        │       ├── [package].cfg      # Runtime config
        │       ├── [package].save     # Save/apply CGI handler
        │       └── [package].rc.template  # Config template
        ├── usr/
        │   ├── lib/
        │   │   └── cgi-bin/
        │   │       └── [package].cgi  # Web interface CGI
        │   └── mww/
        │       └── [package]/
        │           ├── [package]_config_editor.html
        │           └── *.template files
        └── mod/
            └── etc/
                └── default.[package]/
                    └── *.template    # Additional templates
```

### Key Files

#### 1. Makefile (.mk)
- Use `$(PKG_INIT_BIN, version)` for binary packages
- Define installation targets with proper permissions:

```makefile
$(pkg)-install:
	# Deploy CGI scripts
	$(INSTALL_FILE) ./files/root/usr/lib/cgi-bin/*.cgi $(FREETZ_TARGET)/usr/lib/cgi-bin/
	
	# Deploy config files with write permissions
	$(INSTALL_FILE) ./files/root/usr/mww/*/conf/*.template $(TARGET_DIR)/usr/mww/[package]/conf/
	chmod a+rw $(TARGET_DIR)/usr/mww/[package]/conf/*.template
	
	# Deploy init script as executable
	$(INSTALL_FILE) ./files/root/etc/init.d/rc.* $(FREETZ_TARGET)/etc/init.d/
```

#### 2. Config.in
- Provide clear help text with URLs
- Document default paths and behaviors

```
config FREETZ_PACKAGE_[PACKAGE]
	bool "[Package Name]"
	select FREETZ_LIB_libcrypto if PACKAGE_NEEDS_SSL
	default n
	help
		Package description.
		
		Access the configuration (e.g., http://fritz.box:81/cgi-bin/conf/[package])
```

---

## Configuration Framework (modconf)

### Understanding freetz-ng's Config Pipeline

**CRITICAL**: freetz-ng uses a framework-driven configuration system, not ad-hoc file writes. Understanding this pipeline is essential for ANY package with persistent configuration.

#### The modconf System

freetz-ng's `modconf` tool manages package configuration through a two-file system:

1. **Default Config Template**: `/mod/etc/default.<package>/<package>.cfg`
   - Shipped with package
   - Contains `export <PKG>_<VAR>=default_value` declarations
   - Defines which variables exist and their defaults
   - Used by modconf to discover configurable variables

2. **Saved Config**: `/mod/etc/conf/<package>.cfg`
   - Created/updated by user through web UI
   - Contains only user-modified values
   - Sourced after default config (overrides defaults)

#### Variable Discovery

```bash
# modconf discovers variables by sourcing the default cfg
modconf vars <package>

# This ONLY works if variables are exported:
# In /mod/etc/default.<package>/<package>.cfg:
export PACKAGE_ENABLED='no'
export PACKAGE_BASEDIR='/var/media/ftp/package'
export PACKAGE_NICE='5'

# If not exported → modconf won't list it → won't be saved!
```

### System Variables vs Runtime Pass-Through

**Critical Distinction**: Packages often need two types of variables:

#### 1. System Configuration (consumed by init scripts)

```bash
# /mod/etc/default.rtorrent/rtorrent.cfg
export RTORRENT_ENABLED='no'           # Enable daemon
export RTORRENT_BASEDIR='/var/media/ftp/rtorrent'  # Installation path
export RTORRENT_NICE='5'               # Process priority
export RTORRENT_CONFIG_WAIT='120'      # Boot wait time (0=immediate, >0=wait for USB/network)

# Init script reads these:
[ -r /mod/etc/conf/rtorrent.cfg ] && . /mod/etc/conf/rtorrent.cfg

if [ "$RTORRENT_ENABLED" = "yes" ]; then
    start_daemon "$RTORRENT_BASEDIR"
fi
```

#### 2. Runtime Pass-Through (for application config files)

Sometimes you need web UI to capture settings that go into application config (e.g., `.rtorrent.rc`), not used directly by init scripts:

```bash
# Export so modconf captures them from form POST
export RTORRENT_PORT='5000'            # rtorrent SCGI port
export RTORRENT_DL_RATE='0'            # Download rate limit
export RTORRENT_UL_RATE='0'            # Upload rate limit

# These are NOT read by init script!
# They are captured from form, saved to /mod/etc/conf/<pkg>.cfg
# Then pkg_apply_save() reads them and writes to .rtorrent.rc
```

**Document this clearly** in default config:

```bash
# System variables (used by init script)
export RTORRENT_ENABLED='no'
export RTORRENT_BASEDIR='/var/media/ftp/rtorrent'

# Runtime pass-through (exported only to allow POST capture)
# These are written to .rtorrent.rc by save hook, not used by init script
export RTORRENT_PORT='5000'
export RTORRENT_DL_RATE='0'
```

### Save Flow Architecture

#### The Save Hook Script

Packages provide: `/mod/etc/default.<package>/<package>.save`

This script defines hooks called by the framework during save operations:

```bash
#!/bin/sh

# Called BEFORE framework saves /mod/etc/conf/<pkg>.cfg
pkg_pre_save() {
    # Use for:
    # - Pre-flight checks (directory existence, permissions)
    # - Validation that can reject save
    # - Preparing environment
    
    # DO NOT:
    # - Try to read POST data (framework may have consumed it)
    # - Update runtime config files (values not saved yet!)
    
    # Example: Validate base directory
    if [ -n "$RTORRENT_BASEDIR" ] && [ "$RTORRENT_ENABLED" = "yes" ]; then
        if [ ! -d "$RTORRENT_BASEDIR" ]; then
            echo "Warning: Base directory does not exist" >&2
            # Don't fail save - directory may be mounted later
        fi
    fi
}

# Called AFTER framework saves /mod/etc/conf/<pkg>.cfg
pkg_apply_save() {
    # Use for:
    # - Reading saved values from /mod/etc/conf/<pkg>.cfg
    # - Updating runtime config files (.rc, .conf, etc.)
    # - Applying changes that depend on new values
    
    # Source the SAVED config to get new values
    [ -r /mod/etc/conf/rtorrent.cfg ] && . /mod/etc/conf/rtorrent.cfg
    
    # Now update runtime files with NEW values
    local rc_file="${RTORRENT_BASEDIR%/}/.rtorrent.rc"
    
    if [ -f "$rc_file" ]; then
        # Update runtime config with new values
        update_rtorrent_rc "$rc_file"
    fi
}
```

#### Save Flow Timeline

```
User clicks "Save" in web UI
    ↓
1. Framework collects form POST data
    ↓
2. Framework calls pkg_pre_save()
    - Variables contain NEW values from form (already in environment)
    - But /mod/etc/conf/<pkg>.cfg still has OLD values
    - DO NOT update runtime files here!
    ↓
3. Framework writes /mod/etc/conf/<pkg>.cfg
    - New values now persisted
    ↓
4. Framework calls pkg_apply_save()
    - Source /mod/etc/conf/<pkg>.cfg to get saved values
    - NOW safe to update runtime config files
    ↓
5. Framework completes, shows success message
```

### Common Save Flow Pitfalls

#### Pitfall 1: Updating Runtime Config Too Early

```bash
# WRONG - in pkg_pre_save()
pkg_pre_save() {
    # BUG: Reading from /mod/etc/conf/<pkg>.cfg here gets OLD values!
    [ -r /mod/etc/conf/rtorrent.cfg ] && . /mod/etc/conf/rtorrent.cfg
    update_rtorrent_rc "${RTORRENT_BASEDIR}/.rtorrent.rc"
    # Result: Runtime file updated with old values
}

# CORRECT - in pkg_apply_save()
pkg_apply_save() {
    # Framework has saved new values, safe to read and apply
    [ -r /mod/etc/conf/rtorrent.cfg ] && . /mod/etc/conf/rtorrent.cfg
    update_rtorrent_rc "${RTORRENT_BASEDIR}/.rtorrent.rc"
}
```

#### Pitfall 2: Trying to Read POST Data in Hooks

```bash
# WRONG - POST data not accessible
pkg_pre_save() {
    local basedir=$(cgi_param basedir)  # Returns empty!
    local port=$(cgi_param port)        # Returns empty!
    # Framework has already consumed/processed POST
}

# CORRECT - values already in environment
pkg_pre_save() {
    # Variables exported from default cfg are already populated
    # from form POST by framework before calling this hook
    if [ -n "$RTORRENT_BASEDIR" ]; then
        validate_directory "$RTORRENT_BASEDIR"
    fi
}
```

#### Pitfall 3: Implicit Restart on Save

```bash
# WRONG - restarting service automatically
pkg_apply_save() {
    update_config
    /etc/init.d/rc.rtorrent restart  # Unexpected restart!
}

# CORRECT - only save config, let user restart explicitly
pkg_apply_save() {
    update_config
    # User must click separate "Restart" button if needed
}
```

### Form Field Naming

Form field names must align with modconf variable expectations:

```html
<!-- HTML form in CGI -->
<input type="text" name="basedir" value="$RTORRENT_BASEDIR">
<input type="text" name="port" value="$RTORRENT_PORT">

<!-- Framework maps these to: -->
<!-- basedir → RTORRENT_BASEDIR -->
<!-- port → RTORRENT_PORT -->
```

**Rules:**
- Form field name `basedir` maps to `<PKG>_BASEDIR`
- Form field name `enabled` maps to `<PKG>_ENABLED`
- Convention: lowercase field names, uppercase variable names
- Check existing packages for established patterns

**Debug checklist when values don't save:**

```bash
# 1. Is variable exported in default cfg?
cat /mod/etc/default.rtorrent/rtorrent.cfg | grep "^export.*BASEDIR"

# 2. Does modconf see it?
modconf vars rtorrent | grep BASEDIR

# 3. Is form field name correct?
# Check CGI for: <input name="basedir" ...>

# 4. Is saved config updated?
cat /mod/etc/conf/rtorrent.cfg | grep BASEDIR

# 5. Check save hook exists and is executable
ls -la /mod/etc/default.rtorrent/rtorrent.save
```

### Complete Save Hook Template

```bash
#!/bin/sh

# Load saved config if it exists
[ -r /mod/etc/conf/rtorrent.cfg ] && . /mod/etc/conf/rtorrent.cfg

pkg_pre_save() {
    # Pre-flight validation
    # Variables contain NEW form values (from environment)
    
    # Example: Check if enabled requires base directory
    if [ "$RTORRENT_ENABLED" = "yes" ] && [ -z "$RTORRENT_BASEDIR" ]; then
        echo "Error: Base directory required when enabled" >&2
        return 1  # Abort save
    fi
    
    # Example: Warn about filesystem
    if [ -n "$RTORRENT_BASEDIR" ]; then
        local fstype=$(df -T "$RTORRENT_BASEDIR" 2>/dev/null | tail -1 | awk '{print $2}')
        if [ "$fstype" != "ext4" ] && [ "$fstype" != "ext3" ]; then
            echo "Warning: $fstype filesystem not recommended, use ext4" >&2
        fi
    fi
    
    return 0  # Allow save to proceed
}

pkg_apply_save() {
    # Apply changes AFTER framework has saved config
    # Re-source to get persisted values
    [ -r /mod/etc/conf/rtorrent.cfg ] && . /mod/etc/conf/rtorrent.cfg
    
    # Update runtime config file
    local rc_file="${RTORRENT_BASEDIR%/}/.rtorrent.rc"
    
    if [ "$RTORRENT_ENABLED" = "yes" ] && [ -n "$RTORRENT_BASEDIR" ]; then
        # Ensure base directory exists
        mkdir -p "$RTORRENT_BASEDIR" 2>/dev/null
        
        # Create or update runtime config
        if [ ! -f "$rc_file" ]; then
            # Create from template
            cp /mod/etc/default.rtorrent/rtorrent.rc.template "$rc_file"
        fi
        
        # Update with current values
        sed -i "s|^scgi_port = .*|scgi_port = 127.0.0.1:${RTORRENT_PORT}|" "$rc_file"
        sed -i "s|^download_rate = .*|download_rate = ${RTORRENT_DL_RATE}|" "$rc_file"
        sed -i "s|^upload_rate = .*|upload_rate = ${RTORRENT_UL_RATE}|" "$rc_file"
    fi
    
    return 0
}

# If save is forced (e.g., command-line), call hooks in order
case "$1" in
    save)
        pkg_pre_save && pkg_apply_save
        ;;
esac
```

### Deployment Checklist for Config Files

When deploying configuration system:

```bash
# deploy-package.sh

# 1. Deploy default config template
cat make/pkgs/package/files/root/etc/default.package/package.cfg | \
    sshpass -p $DEVICE_PASS ssh $DEVICE_USER@$DEVICE_IP \
    "mkdir -p /mod/etc/default.package && \
     cat > /mod/etc/default.package/package.cfg && \
     chmod 644 /mod/etc/default.package/package.cfg"

# 2. Deploy save hook script
cat make/pkgs/package/files/root/etc/default.package/package.save | \
    sshpass -p $DEVICE_PASS ssh $DEVICE_USER@$DEVICE_IP \
    "cat > /mod/etc/default.package/package.save && \
     chmod 755 /mod/etc/default.package/package.save"

# 3. Verify modconf sees variables
echo "Verifying modconf registration..."
sshpass -p $DEVICE_PASS ssh $DEVICE_USER@$DEVICE_IP "modconf vars package"
```

### Testing Config System

```bash
# 1. Check variable registration
modconf vars package

# Expected output:
# PACKAGE_ENABLED
# PACKAGE_BASEDIR
# PACKAGE_PORT
# ...

# 2. Check default values
modconf defaults package

# 3. Simulate save (without web UI)
modconf set package ENABLED=yes BASEDIR=/tmp/test
modconf save package

# 4. Verify saved config
cat /mod/etc/conf/package.cfg

# 5. Check if save hook executed
# (Add debug logging to pkg_apply_save() during testing)
```

---

## CGI Script Development

### Basic Structure

CGI scripts in freetz-ng use `libmodcgi.sh` for parameter handling and must support both HTML and AJAX modes.

```bash
#!/bin/sh

DAEMON=packagename
. /etc/init.d/modlibrc

# Check for AJAX mode
AJAX_MODE=$(cgi_param ajax)

if [ "$AJAX_MODE" = "1" ]; then
	# AJAX JSON response handler
	ACTION=$(cgi_param action)
	
	# Output JSON wrapper (needed for parsing)
	cat << EOF
Content-Type: text/html; charset=UTF-8

<style>
.ajax-json-box { display: none; }
</style>
<div class="ajax-json-box"><div class="ajax-json-content"><pre>Content-Type: application/json

EOF
	
	case "$ACTION" in
		read_file)
			# Handle file read
			;;
		write_file)
			# Handle file write
			;;
		*)
			echo '{"error": "Unknown action"}'
			;;
	esac
	
	# Close JSON wrapper
	echo '</pre></div></div>'
	exit 0
fi

# Regular HTML mode
cgi_begin "$(lang de:"Titel" en:"Title")"
# ... HTML form ...
cgi_end
```

### Critical CGI Patterns

#### 1. JSON Response Wrapper
**IMPORTANT**: freetz-ng CGI must return HTML-wrapped JSON, not plain JSON:

```bash
# Correct wrapper structure
cat << EOF
<div class="ajax-json-box"><div class="ajax-json-content"><pre>Content-Type: application/json

EOF

echo '{"success": true, "data": "value"}'

echo '</pre></div></div>'
```

JavaScript must parse this format:

```javascript
const response = await fetch('/cgi-bin/conf/package?ajax=1&action=read');
const text = await response.text();

// Find JSON marker
const marker = 'Content-Type: application/json';
const markerPos = text.indexOf(marker);
if (markerPos === -1) throw new Error('Invalid response');

// Extract JSON by counting braces
const firstBrace = text.indexOf('{', markerPos + marker.length);
let braceCount = 0, jsonEnd = -1;
for (let i = firstBrace; i < text.length; i++) {
    if (text[i] === '{') braceCount++;
    else if (text[i] === '}') {
        braceCount--;
        if (braceCount === 0) {
            jsonEnd = i + 1;
            break;
        }
    }
}
const jsonText = text.substring(firstBrace, jsonEnd);
const data = JSON.parse(jsonText);
```

#### 2. File Access Whitelist

Always implement security whitelist for file operations:

```bash
read_file)
	FILE_PATH=$(cgi_param file)
	
	# Expand basename shortcuts
	case "$FILE_PATH" in
		config.php|*.template)
			# Auto-detect installation path
			if [ -d "/mod/external/usr/mww/package" ]; then
				FILE_PATH="/mod/external/usr/mww/package/conf/$FILE_PATH"
			elif [ -d "/usr/mww/package" ]; then
				FILE_PATH="/usr/mww/package/conf/$FILE_PATH"
			fi
			;;
	esac
	
	# Security: prevent directory traversal
	case "$FILE_PATH" in
		*../*|*/../*|../*)
			echo '{"error": "Directory traversal not allowed"}'
			exit 0
			;;
	esac
	
	# Whitelist allowed paths
	ALLOWED=0
	case "$FILE_PATH" in
		/var/media/ftp/*/.config.rc|\
		/var/media/ftp/*/*/.config.rc|\
		/tmp/.config.rc|\
		/mod/etc/default.package/*.template)
			ALLOWED=1
			;;
		*)
			# Check application config files
			case "$FILE_PATH" in
				/usr/mww/package/conf/*|\
				/mod/external/usr/mww/package/conf/*)
					case "$FILE_PATH" in
						*.php|*.ini|*.template) ALLOWED=1 ;;
					esac
					;;
			esac
			
			# Check dynamic BASEDIR
			if [ "$ALLOWED" = "0" ]; then
				[ -r /mod/etc/conf/package.cfg ] && . /mod/etc/conf/package.cfg
				BASEDIR_RC="${PACKAGE_BASEDIR%/}/.config.rc"
				[ "$FILE_PATH" = "$BASEDIR_RC" ] && ALLOWED=1
			fi
			;;
	esac
	
	if [ "$ALLOWED" = "0" ]; then
		echo "{\"error\": \"Access denied: $FILE_PATH\"}"
		exit 0
	fi
	;;
```

#### 3. Backup Before Write

Always create timestamped backups before modifying files:

```bash
write_file)
	FILE_PATH=$(cgi_param file)
	CONTENT=$(cgi_param content)
	
	# Create backup if file exists
	if [ -f "$FILE_PATH" ]; then
		TIMESTAMP=$(date +%Y-%m-%d-%H-%M-%S)
		BACKUP_FILE="${FILE_PATH}.${TIMESTAMP}"
		cp "$FILE_PATH" "$BACKUP_FILE" 2>/dev/null
	fi
	
	# Write content
	if echo "$CONTENT" > "$FILE_PATH" 2>/dev/null; then
		echo "{\"success\": true, \"file\": \"$FILE_PATH\"}"
	else
		# Rollback on failure
		if [ -n "$BACKUP_FILE" ] && [ -f "$BACKUP_FILE" ]; then
			mv "$BACKUP_FILE" "$FILE_PATH" 2>/dev/null
		fi
		echo "{\"error\": \"Failed to write file\"}"
	fi
	;;
```

#### 4. Basename Expansion Pattern

**Support both full paths and short names** for user convenience:

```bash
read_file)
	FILE_PATH=$(cgi_param file)
	
	# Expand basename shortcuts
	case "$FILE_PATH" in
		config.php|*.template)
			# Auto-detect installation path
			if [ -d "/mod/external/usr/mww/package" ]; then
				FILE_PATH="/mod/external/usr/mww/package/conf/$FILE_PATH"
			elif [ -d "/usr/mww/package" ]; then
				FILE_PATH="/usr/mww/package/conf/$FILE_PATH"
			fi
			;;
		.config.rc)
			# Use basedir from parameter
			BASEDIR=$(cgi_param basedir)
			FILE_PATH="${BASEDIR%/}/.config.rc"
			;;
		*/*)
			# Already a full path, use as-is
			;;
	esac
	
	# Continue with whitelist check...
	;;
```

**Benefits:**
- Editors can use short names: `file=config.php` instead of full path
- Automatic path detection (external vs standard)
- More maintainable JavaScript code

#### 5. Delete as Rename

Never actually delete files - rename with timestamp for recovery:

```bash
delete_config)
	BASEDIR=$(cgi_param basedir)
	CONFIG_FILE="$BASEDIR/.config.rc"
	
	# Security checks...
	
	# Rename instead of delete
	TIMESTAMP=$(date +%Y-%m-%d-%H-%M-%S)
	BACKUP_FILE="${CONFIG_FILE}.${TIMESTAMP}"
	if mv "$CONFIG_FILE" "$BACKUP_FILE" 2>/dev/null; then
		echo "{\"success\": true, \"message\": \"File archived to: ${BACKUP_FILE##*/}\"}"
	else
		echo '{"success": false, "message": "Failed to archive file"}'
	fi
	;;
```

**CRITICAL**: In AJAX handlers, avoid premature `exit 0` before closing the JSON wrapper:

```bash
# WRONG - exits before closing wrapper
if [ -z "$BASEDIR" ]; then
	echo '{"success": false, "message": "No basedir"}'
	exit 0  # BAD! Leaves HTML unclosed
fi

# CORRECT - use elif chain
if [ -z "$BASEDIR" ]; then
	echo '{"success": false, "message": "No basedir"}'
elif [ ! -f "$FILE" ]; then
	echo '{"success": false, "message": "File not found"}'
else
	# Process file
	echo '{"success": true}'
fi
# Now safe to close wrapper and exit
```

---

## Web Interface Editors

### HTML Editor Structure

Use ACE Editor for syntax-highlighted configuration editing:

```html
<!DOCTYPE html>
<html>
<head>
	<meta charset="UTF-8">
	<title>Config Editor</title>
	<script src="/ace/ace.js"></script>
	<style>
		body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
		#editor { height: 500px; border: 1px solid #ccc; }
		#status { padding: 10px; margin: 10px 0; border-radius: 4px; }
	</style>
</head>
<body>
	<h1 id="title">Configuration Editor</h1>
	
	<!-- File selector for multi-file editors -->
	<select id="fileSelector" onchange="switchFile()">
		<option value="config">config.php</option>
		<option value="access">access.ini</option>
	</select>
	
	<button onclick="loadFileFromServer()" id="btnLoad">Load</button>
	<button onclick="saveFileToServer()" id="btnSave">Save</button>
	<button onclick="loadTemplate()" id="btnTemplate">Load Template</button>
	
	<div id="status">Ready</div>
	<div id="editor"></div>
	
	<script>
		// Initialize ACE editor
		const editor = ace.edit("editor");
		editor.setTheme("ace/theme/monokai");
		editor.session.setMode("ace/mode/php"); // or ini, sh, etc.
		editor.setOptions({
			fontSize: "14px",
			showPrintMargin: false,
			enableBasicAutocompletion: true,
			enableLiveAutocompletion: true
		});
		
		// Translations for multi-language support
		const translations = {
			en: {
				title: "Configuration Editor",
				btnLoad: "Load File",
				btnSave: "Save File",
				btnTemplate: "Load Template",
				statusReady: "Ready",
				statusLoading: "Loading...",
				statusSaved: "Saved successfully ✓",
				errorLoadFailed: "Failed to load file",
				confirmReload: "Reload file? Unsaved changes will be lost."
			},
			de: { /* German translations */ },
			it: { /* Italian translations */ },
			fr: { /* French translations */ },
			es: { /* Spanish translations */ }
		};
		
		let currentLang = 'en';
		let currentFile = 'config';
		
		// Auto-detect language from browser
		function detectLanguage() {
			const browserLang = navigator.language.split('-')[0];
			return translations.hasOwnProperty(browserLang) ? browserLang : 'en';
		}
		
		// FritzBox detection for auto-path determination
		function isFritzBox() {
			return window.location.pathname.startsWith('/rtorrent/');
		}
		
		// Get base path (external vs standard)
		function getBasePath() {
			// Try external path first
			return '/mod/external/usr/mww/package/conf';
		}
		
		// Load file from server
		async function loadFileFromServer() {
			const t = translations[currentLang];
			document.getElementById('status').textContent = t.statusLoading;
			
			const filePath = getFilePath();
			
			try {
				const url = '/cgi-bin/conf/package';
				const params = new URLSearchParams({
					ajax: '1',
					action: 'read_file',
					file: filePath
				});
				
				const response = await fetch(`${url}?${params.toString()}`);
				const text = await response.text();
				
				// Parse JSON from HTML wrapper
				const marker = 'Content-Type: application/json';
				const markerPos = text.indexOf(marker);
				if (markerPos === -1) throw new Error('Invalid response');
				
				const firstBrace = text.indexOf('{', markerPos + marker.length);
				if (firstBrace === -1) throw new Error('No JSON found');
				
				let braceCount = 0, jsonEnd = -1;
				for (let i = firstBrace; i < text.length; i++) {
					if (text[i] === '{') braceCount++;
					else if (text[i] === '}') {
						braceCount--;
						if (braceCount === 0) {
							jsonEnd = i + 1;
							break;
						}
					}
				}
				
				if (jsonEnd === -1) throw new Error('Incomplete JSON');
				const data = JSON.parse(text.substring(firstBrace, jsonEnd));
				
				if (data.success && data.content !== undefined) {
					editor.setValue(data.content, -1);
					editor.clearSelection();
					document.getElementById('status').textContent = t.statusReady;
				} else {
					throw new Error(data.error || 'Load failed');
				}
			} catch (err) {
				console.error('Load error:', err);
				document.getElementById('status').textContent = t.errorLoadFailed + ': ' + err.message;
				document.getElementById('status').style.background = '#dc3545';
				setTimeout(() => {
					document.getElementById('status').style.background = '';
				}, 3000);
			}
		}
		
		// Save file to server
		async function saveFileToServer() {
			const t = translations[currentLang];
			document.getElementById('status').textContent = 'Saving...';
			
			const filePath = getFilePath();
			const content = editor.getValue();
			
			try {
				const url = '/cgi-bin/conf/package';
				const params = new URLSearchParams({
					ajax: '1',
					action: 'write_file',
					file: filePath,
					content: content
				});
				
				const response = await fetch(`${url}?${params.toString()}`);
				const text = await response.text();
				
				// Parse JSON (same as load)
				const marker = 'Content-Type: application/json';
				const markerPos = text.indexOf(marker);
				if (markerPos === -1) throw new Error('Invalid response');
				
				const firstBrace = text.indexOf('{', markerPos + marker.length);
				let braceCount = 0, jsonEnd = -1;
				for (let i = firstBrace; i < text.length; i++) {
					if (text[i] === '{') braceCount++;
					else if (text[i] === '}') {
						braceCount--;
						if (braceCount === 0) {
							jsonEnd = i + 1;
							break;
						}
					}
				}
				
				const data = JSON.parse(text.substring(firstBrace, jsonEnd));
				
				if (data.success) {
					document.getElementById('status').textContent = t.statusSaved;
					document.getElementById('status').style.background = '#28a745';
					setTimeout(() => {
						document.getElementById('status').textContent = t.statusReady;
						document.getElementById('status').style.background = '';
					}, 2000);
				} else {
					throw new Error(data.error || 'Save failed');
				}
			} catch (err) {
				console.error('Save error:', err);
				document.getElementById('status').textContent = 'Error: ' + err.message;
				document.getElementById('status').style.background = '#dc3545';
			}
		}
		
		// Load template from server
		async function loadTemplate() {
			const confirmed = confirm(translations[currentLang].confirmReload);
			if (!confirmed) return;
			
			const templatePath = getBasePath() + '/' + currentFile + '.template';
			
			// Use same logic as loadFileFromServer but with template path
			// ...
		}
		
		// Auto-load on page load if on FritzBox
		window.addEventListener('load', () => {
			currentLang = detectLanguage();
			applyTranslations();
			
			if (isFritzBox()) {
				loadFileFromServer();
			}
		});
	</script>
</body>
</html>
```

### Key Editor Patterns

1. **Multi-language from start**: Include all translations in a single object
2. **Auto-detection**: Detect FritzBox environment and load automatically
3. **Template support**: Load .template files from server, not hardcoded
4. **Status feedback**: Visual feedback for all operations with auto-clear
5. **Error handling**: Catch and display errors gracefully
6. **Confirmation prompts**: Ask before discarding unsaved changes

---

## Init Scripts

Init scripts (`rc.*`) handle daemon lifecycle and must integrate with freetz-ng's modlib system.

### Template Structure

```bash
#!/bin/sh

DAEMON=packagename
DAEMON_BIN=packagename
PID_FILE=/var/run/$DAEMON.pid
. /etc/init.d/modlibrc

# Load persistent configuration
[ -r /mod/etc/conf/package.cfg ] && . /mod/etc/conf/package.cfg

# Constants
TEMPLATE_FILE="/mod/etc/default.package/package.rc.template"
USERNAME=package_user
GROUPNAME=users

# Check if daemon is running
is_running() {
	if [ -f "$PID_FILE" ]; then
		local pid=$(cat "$PID_FILE" 2>/dev/null)
		if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
			return 0
		fi
	fi
	pgrep -x $DAEMON_BIN >/dev/null 2>&1 && return 0
	return 1
}

# Wait for time synchronization (critical for boot)
wait_for_time_sync() {
	local max_wait="${1:-120}"
	local min_valid_year=2025
	local elapsed=0
	
	while [ $elapsed -lt $max_wait ]; do
		local current_year=$(date +%Y)
		if [ "$current_year" -ge $min_valid_year ]; then
			return 0
		fi
		sleep 2
		elapsed=$((elapsed + 2))
	done
	
	return 1
}

# Wait for directory availability (USB mount, etc.)
wait_for_directory() {
	local dir="$1"
	local max_wait="${2:-120}"
	local elapsed=0
	
	while [ $elapsed -lt $max_wait ]; do
		if [ -d "$dir" ]; then
			return 0
		fi
		sleep 2
		elapsed=$((elapsed + 2))
	done
	
	return 1
}

# Start daemon asynchronously (for boot)
start_async() {
	basedir="$1"
	wait_time="${2:-120}"
	
	echo "$(date): Starting $DAEMON asynchronously..." >> /tmp/rc.$DAEMON.log
	
	# Wait for time sync
	if ! wait_for_time_sync "$wait_time"; then
		echo "$(date): Failed - time not synchronized" >> /tmp/rc.$DAEMON.log
		return 1
	fi
	
	# Wait for directory
	if ! wait_for_directory "$basedir" "$wait_time"; then
		echo "$(date): Failed - directory not accessible" >> /tmp/rc.$DAEMON.log
		return 1
	fi
	
	# Start daemon
	if start_daemon "$basedir"; then
		echo "$(date): $DAEMON started successfully" >> /tmp/rc.$DAEMON.log
	else
		echo "$(date): Failed to start $DAEMON" >> /tmp/rc.$DAEMON.log
		return 1
	fi
}

# Start daemon (core logic)
start_daemon() {
	basedir="$1"
	
	# Create required directories
	mkdir -p "$basedir/data" "$basedir/logs" 2>/dev/null
	
	# Start with start-stop-daemon
	start-stop-daemon -S -b -m -p "$PID_FILE" \
		-N "${PACKAGE_NICE:-5}" \
		-c "$USERNAME:$GROUPNAME" \
		-- /usr/bin/$DAEMON_BIN --config "$basedir/.config.rc"
	
	return $?
}

# Synchronous start (for manual 'start')
start() {
	echo "Starting $DAEMON daemon..."
	
	if is_running; then
		echo "failed: $DAEMON is already running."
		exit 1
	fi
	
	modlib_add_user_and_group $USERNAME $GROUPNAME
	
	basedir="${PACKAGE_BASEDIR%/}"
	
	if [ -z "$basedir" ]; then
		echo "failed: No base directory configured."
		exit 1
	fi
	
	# Check directory immediately (no wait for manual start)
	if [ ! -d "$basedir" ]; then
		echo "failed: Directory '$basedir' not accessible."
		exit 1
	fi
	
	if start_daemon "$basedir"; then
		echo 'done.'
	else
		echo 'failed.'
		exit 1
	fi
}

# Stop daemon
stop() {
	echo "Stopping $DAEMON daemon..."
	
	if ! is_running; then
		echo "failed: $DAEMON is not running."
		return 1
	fi
	
	start-stop-daemon -K -q -p "$PID_FILE"
	
	# Wait for process to exit
	local timeout=10
	while [ $timeout -gt 0 ] && is_running; do
		sleep 1
		timeout=$((timeout - 1))
	done
	
	if is_running; then
		# Force kill if still running
		kill -9 $(cat "$PID_FILE" 2>/dev/null) 2>/dev/null
		rm -f "$PID_FILE"
	fi
	
	echo 'done.'
}

# Main case statement
case $1 in
	""|load)
		modlib_add_user_and_group $USERNAME $GROUPNAME
		modreg cgi 'package' 'Package Name'
		modreg daemon $DAEMON
		
		# During boot/load, start asynchronously
		if [ "$PACKAGE_ENABLED" = "yes" ]; then
			[ -r /etc/options.cfg ] && . /etc/options.cfg
			basedir="${PACKAGE_BASEDIR%/}"
			wait_time="${PACKAGE_CONFIG_WAIT:-120}"
			
			if [ -n "$basedir" ]; then
				echo "$DAEMON will start in background (waiting for resources)."
				# Launch in background with nohup
				(
					# Re-source config in subshell
					. /etc/init.d/modlibrc
					[ -r /mod/etc/conf/package.cfg ] && . /mod/etc/conf/package.cfg
					start_async "$basedir" "$wait_time"
				) >/dev/null 2>&1 &
			else
				echo "$DAEMON: base directory not configured, skipped."
			fi
		fi
		;;
	unload)
		modunreg daemon $DAEMON
		modunreg cgi 'package'
		stop
		;;
	start)
		start
		;;
	stop)
		stop
		;;
	restart)
		stop
		sleep 1
		start
		;;
	status)
		modlib_status
		;;
	*)
		echo "Usage: $0 [load|unload|start|stop|restart|status]" 1>&2
		exit 1
		;;
esac

exit 0
```

### Critical Init Script Patterns

#### 1. Avoid `local` in Case Statements

**PROBLEM**: Using `local` for variable assignment in case statements can fail:

```bash
# WRONG - may fail with empty variables
case $1 in
	load)
		local basedir="${PACKAGE_BASEDIR%/}"
		if [ -n "$basedir" ]; then  # May be empty even if PACKAGE_BASEDIR is set!
			echo "Starting..."
		fi
		;;
esac
```

```bash
# CORRECT - direct assignment without local
case $1 in
	load)
		basedir="${PACKAGE_BASEDIR%/}"
		if [ -n "$basedir" ]; then  # Works correctly
			echo "Starting..."
		fi
		;;
esac
```

#### 2. Async Boot Start Pattern

During boot (`load` action), never block - use background subshell:

```bash
if [ "$PACKAGE_ENABLED" = "yes" ]; then
	basedir="${PACKAGE_BASEDIR%/}"
	wait_time="${PACKAGE_CONFIG_WAIT:-120}"
	
	if [ -n "$basedir" ]; then
		if [ "$wait_time" = "0" ]; then
			# Synchronous start when CONFIG_WAIT=0 (no wait)
			echo "$DAEMON starting synchronously..."
			modlib_add_user_and_group $USERNAME $GROUPNAME
			start_daemon "$basedir"
		else
			# Asynchronous start with wait for resources
			echo "$DAEMON will start in background."
			# Critical: Launch in subshell to not block boot
			(
				# Must re-source config in subshell!
				. /etc/init.d/modlibrc
				[ -r /mod/etc/conf/package.cfg ] && . /mod/etc/conf/package.cfg
				
				# Wait for resources then start
				start_async "$basedir" "$wait_time"
			) >/dev/null 2>&1 &  # & = background
		fi
	fi
fi
```

**Note**: Set `CONFIG_WAIT=0` for **synchronous start** (immediate, no background wait). Use this when:
- Base directory is guaranteed available at boot (internal storage)
- Testing/debugging startup issues
- No USB/network dependencies

Default `CONFIG_WAIT=120` for **asynchronous start** (waits for USB/network). Use this when:
- Base directory on USB drive or NAS
- Network shares need time to mount
- Time sync required for SSL/TLS

#### 3. Wait Conditions

Always wait for resources during boot (when CONFIG_WAIT > 0):

- **Time sync**: Prevent SSL/certificate errors
- **Directory availability**: Wait for USB mounts
- **Configurable timeout**: Allow override via config

#### 4. `start-stop-daemon` + `sh -c`: Quote the Whole Command

**PROBLEM**: Unquoted `sh -c` invocations can silently run the wrong thing (e.g. only `exec`), producing “no output”, no daemon, and confusing PID handling.

**RULES**:
- Pass the full command as a *single* quoted string to `sh -c`.
- Prefer `exec` inside the `-c` string so the shell is replaced by the daemon process.
- If the application does not daemonize/fork reliably, use `start-stop-daemon -b` to background it.

```bash
# WRONG ("-c" sees only "exec", rest becomes $0/$1...)
start-stop-daemon -S -b -m -p "$PID_FILE" -- /bin/sh -c exec /usr/bin/daemon --flag \
	>>/tmp/daemon.out 2>>/tmp/daemon.err

# CORRECT (everything is part of one quoted string)
start-stop-daemon -S -b -m -p "$PID_FILE" -- /bin/sh -c \
	"exec /usr/bin/daemon --flag >>/tmp/daemon.out 2>>/tmp/daemon.err"
```

---

## Template System

### Purpose

Templates separate default configurations from user configurations:
- **Template files** (`.template`): Default/starter configs, read-only, shipped with package
- **Config files**: User-customized configs, writable, created from templates

### Template File Locations

```
/mod/etc/default.package/
├── package.rc.template          # Main config template
└── other.conf.template          # Additional templates

/mod/external/usr/mww/package/conf/  # Or /usr/mww/package/conf/
├── config.php.template
├── access.ini.template
└── plugins.ini.template
```

### Deploying Templates

In `.mk` file:

```makefile
$(pkg)-install:
	# Install templates
	$(INSTALL_FILE) ./files/root/mod/etc/default.package/*.template \
		$(TARGET_DIR)/mod/etc/default.package/
	
	# Config files need write permissions
	$(INSTALL_FILE) ./files/root/usr/mww/package/conf/*.template \
		$(TARGET_DIR)/usr/mww/package/conf/
	chmod a+rw $(TARGET_DIR)/usr/mww/package/conf/*.template
```

### Template Loading in Web Editor

```javascript
async function loadTemplate() {
	const confirmed = confirm('Load template? Current changes will be lost.');
	if (!confirmed) return;
	
	const templatePath = '/mod/etc/default.package/config.template';
	
	try {
		const url = '/cgi-bin/conf/package';
		const params = new URLSearchParams({
			ajax: '1',
			action: 'read_file',
			file: templatePath
		});
		
		const response = await fetch(`${url}?${params.toString()}`);
		// ... parse JSON from HTML wrapper ...
		
		if (data.success && data.content) {
			editor.setValue(data.content, -1);
			document.getElementById('status').textContent = 'Template loaded';
		}
	} catch (err) {
		alert('Failed to load template: ' + err.message);
	}
}
```

### Template in CGI Whitelist

Add template paths to CGI security whitelist:

```bash
case "$FILE_PATH" in
	/mod/etc/default.package/*.template|\
	/usr/mww/package/conf/*.template|\
	/mod/external/usr/mww/package/conf/*.template)
		ALLOWED=1
		;;
esac
```

---

## Deployment Scripts

Create deployment scripts for rapid development iteration without full rebuilds.

### Template Deploy Script

```bash
#!/bin/bash
# deploy-package.sh
# Deploy package files to device for testing

set -e

DEVICE_IP="192.168.178.1"
DEVICE_USER="root"
DEVICE_PASS="yourpassword"

echo "=== Deploying Package ==="

# Step 1: Prepare CGI (process language substitution)
echo "Step 1: Processing language substitution..."
cp make/pkgs/package/files/root/usr/lib/cgi-bin/package.cgi /tmp/package.cgi

bash << 'EOFBASH'
source tools/freetz_functions
modlangsubst "en" /tmp/package.cgi
EOFBASH

if grep -q "error: language not set" /tmp/package.cgi; then
	echo "ERROR: Language substitution failed!"
	exit 1
fi
echo "✓ Language substitution OK"

# Step 2: Deploy CGI
echo "Step 2: Deploying CGI..."
cat /tmp/package.cgi | sshpass -p $DEVICE_PASS ssh $DEVICE_USER@$DEVICE_IP \
	"cat > /mod/external/usr/lib/cgi-bin/package.cgi && chmod +x /mod/external/usr/lib/cgi-bin/package.cgi"
echo "✓ CGI deployed"

# Step 3: Deploy init script
echo "Step 3: Deploying init script..."
cat make/pkgs/package/files/root/etc/init.d/rc.package | sshpass -p $DEVICE_PASS ssh $DEVICE_USER@$DEVICE_IP \
	"cat > /mod/external/etc/init.d/rc.package && chmod +x /mod/external/etc/init.d/rc.package"
echo "✓ Init script deployed"

# Step 4: Deploy config files
echo "Step 4: Deploying config files..."
cat make/pkgs/package/files/root/etc/default.package/package.cfg | sshpass -p $DEVICE_PASS ssh $DEVICE_USER@$DEVICE_IP \
	"mkdir -p /mod/external/etc/default.package && cat > /mod/external/etc/default.package/package.cfg && chmod 644 /mod/external/etc/default.package/package.cfg"
echo "✓ Config deployed"

# Step 5: Deploy HTML editors
echo "Step 5: Deploying HTML editors..."
cat make/pkgs/package/files/root/usr/mww/package/editor.html | sshpass -p $DEVICE_PASS ssh $DEVICE_USER@$DEVICE_IP \
	"mkdir -p /mod/external/usr/mww/package && cat > /mod/external/usr/mww/package/editor.html"
echo "✓ Editor deployed"

# Step 6: Deploy templates
echo "Step 6: Deploying template files..."
for template in make/pkgs/package/files/root/usr/mww/package/conf/*.template; do
	filename=$(basename "$template")
	cat "$template" | sshpass -p $DEVICE_PASS ssh $DEVICE_USER@$DEVICE_IP \
		"mkdir -p /mod/external/usr/mww/package/conf && cat > /mod/external/usr/mww/package/conf/$filename && chmod a+rw /mod/external/usr/mww/package/conf/$filename"
	echo "✓ $filename deployed"
done

echo ""
echo "=== Deployment complete! ==="
echo "Refresh your browser to see changes."
```

### Usage

```bash
# Deploy without rebuilding
./deploy-package.sh

# Restart service to test
ssh root@192.168.178.1 '/etc/init.d/rc.package restart'

# Check logs
ssh root@192.168.178.1 'tail -50 /tmp/rc.package.log'
```

---

## Common Pitfalls

### 1. Wrong CGI URL

**PROBLEM**: URL confusion between physical file path and web path

```javascript
// WRONG (assuming non-existent directory structure)
fetch('/cgi-bin/conf/package?...')

// CORRECT (actual CGI location)
fetch('/cgi-bin/package.cgi?...')
```

**SOLUTION**: Check actual CGI installation path:
```bash
ls /usr/lib/cgi-bin/
# Should show: package.cgi (not conf/package)
```

Use the correct URL: `/cgi-bin/package.cgi`

### 2. Template Path Issues

**PROBLEM**: Hardcoded `/etc/` instead of `/mod/etc/`

```bash
# WRONG
TEMPLATE="/etc/default.package/template.rc"

# CORRECT
TEMPLATE="/mod/etc/default.package/template.rc"
```

freetz-ng uses `/mod/` prefix for persistent storage across reboots.

### 3. Missing Whitelist Entries

**PROBLEM**: Forgetting to add new template paths to security whitelist

```bash
# Add EVERY template path to whitelist
case "$FILE_PATH" in
	/mod/etc/default.package/*.template|\
	/usr/mww/package/conf/*.template|\
	/mod/external/usr/mww/package/conf/*.template)
		ALLOWED=1
		;;
esac
```

### 4. JSON Parsing Failures

**PROBLEM**: Using `.json()` on HTML-wrapped responses

```javascript
// WRONG
const data = await response.json();  // Fails! Response is HTML

// CORRECT
const text = await response.text();
// Extract JSON with marker parsing (see CGI patterns above)
```

### 5. Exit Before Wrapper Close

**PROBLEM**: AJAX handler exits before closing HTML wrapper

```bash
# WRONG
case "$ACTION" in
	read_file)
		if [ ! -f "$FILE" ]; then
			echo '{"error": "Not found"}'
			exit 0  # Leaves wrapper unclosed!
		fi
		;;
esac
echo '</pre></div></div>'  # Never reached!

# CORRECT
case "$ACTION" in
	read_file)
		if [ ! -f "$FILE" ]; then
			echo '{"error": "Not found"}'
		else
			echo '{"success": true}'
		fi
		;;  # Don't exit, fall through to close wrapper
esac
echo '</pre></div></div>'  # Always reached
exit 0
```

### 6. AJAX 404 Errors

**PROBLEM**: AJAX requests return 404

**Symptoms:**
```javascript
// Console shows:
GET /cgi-bin/conf/package?action=read 404 (Not Found)
```

**Root Causes:**
1. Wrong URL in JavaScript
2. Missing symlink in `/cgi-bin/conf/`
3. CGI not deployed to correct location
4. Lighttpd not configured for CGI path

**Debug Steps:**
```bash
# 1. Check actual CGI location
ssh root@device 'ls -la /usr/lib/cgi-bin/package.cgi'
# Should exist and be executable

# 2. Check if using /cgi-bin/conf/ path
ssh root@device 'ls -la /cgi-bin/conf/'
# Should show symlinks or directory

# 3. Test direct access
curl 'http://device/cgi-bin/package.cgi'
# Should return HTML, not 404

# 4. Check JavaScript URL
# If using '/cgi-bin/conf/package', verify Config.in has:
PACKAGE_CGIDIR='conf'

# 5. Check package.cgi for correct shebang
head -1 /usr/lib/cgi-bin/package.cgi
# Should be: #!/bin/sh
```

**Solution:**
- Use consistent URL pattern throughout: `/cgi-bin/conf/package` OR `/cgi-bin/package.cgi`
- Ensure deploy script copies to correct location
- Verify Config.in matches URL pattern

### 7. Forgetting Backup Before Modify

**PROBLEM**: Overwriting user config without backup

```bash
# WRONG - direct overwrite
echo "$NEW_CONTENT" > "$CONFIG_FILE"

# CORRECT - backup first
if [ -f "$CONFIG_FILE" ]; then
	TIMESTAMP=$(date +%Y-%m-%d-%H-%M-%S)
	cp "$CONFIG_FILE" "${CONFIG_FILE}.${TIMESTAMP}"
fi
echo "$NEW_CONTENT" > "$CONFIG_FILE"
```

### 8. Blocking Boot with Synchronous Wait

**PROBLEM**: Init script waits for directory, blocking boot sequence

```bash
# WRONG - blocks boot for 120 seconds!
case $1 in
	load)
		wait_for_directory "$BASEDIR" 120  # Boot waits here!
		start_daemon
		;;
esac

# CORRECT - launch in background
case $1 in
	load)
		(
			wait_for_directory "$BASEDIR" 120
			start_daemon
		) &  # Background process, boot continues
		;;
esac
```

### 9. Editor Validation Ignoring Comments

**PROBLEM**: Syntax validation triggers on comment lines

```javascript
// WRONG - validates commented-out lines
function validateBrackets(line) {
	if (line.indexOf('[') !== -1) {
		// Triggers on: # example = [value]
	}
}

// CORRECT - skip comment lines
function validateBrackets(line) {
	if (line.trim().startsWith('#')) {
		return;  // Skip comments
	}
	if (line.indexOf('[') !== -1) {
		// Only validates actual config lines
	}
}
```

### 10. Modal/Confirmation DOM Placement

**PROBLEM**: Confirmation overlays appear behind wizard or outside container

```html
<!-- WRONG - global overlay -->
<div id="confirmModal" style="position:fixed; z-index:9999">
	<!-- May appear behind wizard or be cut off -->
</div>

<!-- CORRECT - use wizard footer for confirmation -->
<script>
function showDeleteConfirmation() {
	// Replace wizard footer buttons temporarily
	const footer = document.querySelector('.wizard-footer');
	footer.innerHTML = `
		<span>Delete configuration? This cannot be undone.</span>
		<button onclick="cancelDelete()">Cancel</button>
		<button onclick="confirmDelete()">Delete</button>
	`;
}
</script>
```

### 11. Validator Type Mismatches

**PROBLEM**: Validator rejects valid values (e.g., `0.0.0.0`, `16M`)

```javascript
// WRONG - too restrictive IP validation
if (!/^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(value)) {
	// Rejects 0.0.0.0 (valid bind address)
}

// CORRECT - context-aware validation
function validateIP(value, allowAny = true) {
	if (allowAny && value === '0.0.0.0') return true;
	// Standard IP validation
	return /^(\d{1,3}\.){3}\d{1,3}$/.test(value);
}

// WRONG - no size suffix support
if (!/^\d+$/.test(size)) {
	// Rejects "16M" (valid size format)
}

// CORRECT - support common suffixes
function validateSize(value) {
	return /^\d+[KMG]?$/.test(value);
}
```

### 12. CGI Exists But Is Not Executable (`+x`)

**PROBLEM**: Navigating to `/cgi-bin/conf/<pkg>` fails with errors like:

```
Error: No script for '<pkg>/_index'
```

even though the CGI file is present.

**ROOT CAUSE**: The freetz config framework checks that the target CGI is executable (`test -x`). If the file mode is `0644` (or otherwise not executable), it’s treated as “missing”.

**DEBUG**:
```bash
ls -la /usr/lib/cgi-bin/<pkg>.cgi
head -1 /usr/lib/cgi-bin/<pkg>.cgi   # should be: #!/bin/sh
```

**FIX**:
```bash
chmod 755 /usr/lib/cgi-bin/<pkg>.cgi
```

**BUILD-TIME RULE**: Install CGI scripts with an executable mode (e.g. `0755`). Don’t rely on generic “file install” helpers that may default to `0644`.

### 13. Backgrounding vs “Daemon Mode” Are Different Things

**PROBLEM**: Assuming an application’s “daemon/headless” option replaces init-script backgrounding.

**GUIDANCE**:
- `start-stop-daemon -b` controls whether the service is backgrounded by the init system wrapper.
- Some applications have their own “daemon/headless/non-interactive” flag that affects runtime behavior but does **not** necessarily fork into the background.

**Practical rule**: even if the app has a “daemon/headless/background” option, you may still need the init system to background it (`start-stop-daemon -b`) and manage a PID file.

### 14. Upstream Instability After Version Bumps

**SYMPTOMS**: After upgrading a daemon (or a core library it links against), you may see rare boot-time crashes, event-loop errors, or “starts then immediately exits” behavior that didn’t happen before.

**MITIGATIONS** (pragmatic):
- Capture stdout/stderr to files during start so failures aren’t lost.
- Add a short “boot monitor” restart window if the daemon dies shortly after boot.
- Prefer known-stable version pairs when reliability matters more than new features.
- If a regression is suspected, try a rollback or pin to a prior known-good version (with checksums) until upstream stabilizes.

---

## Best Practices

### 1. Multi-Language from Start

Always include translations object, even for internal tools:

```javascript
const translations = {
	en: { title: "Config Editor", btnSave: "Save" },
	de: { title: "Konfigurations-Editor", btnSave: "Speichern" },
	it: { title: "Editor di Configurazione", btnSave: "Salva" },
	fr: { title: "Éditeur de Configuration", btnSave: "Enregistrer" },
	es: { title: "Editor de Configuración", btnSave: "Guardar" }
};
```

### 2. Comprehensive Error Handling

Log errors, show user-friendly messages, provide recovery options:

```javascript
try {
	await saveFile();
	showStatus('Saved successfully', 'success');
} catch (err) {
	console.error('Save failed:', err);
	showStatus('Save failed: ' + err.message, 'error');
	// Keep editor content so user can retry
}
```

```bash
if ! start_daemon "$basedir"; then
	echo "$(date): Failed to start - see logs" >> /tmp/rc.package.log
	# Don't delete PID file, leave traces for debugging
	return 1
fi
```

### 3. Security by Default

- Whitelist > Blacklist for file access
- Validate ALL user input
- Prevent directory traversal (`../`)
- Limit file types and paths
- Never trust URL parameters

### 4. Logging for Debugging

Add strategic logging points:

```bash
echo "$(date): Function started with basedir=$basedir" >> /tmp/rc.package.log
# ... operation ...
echo "$(date): Operation completed successfully" >> /tmp/rc.package.log
```

Use `set -x` during development in init scripts:

```bash
#!/bin/sh
set -x  # Enable debug tracing
exec 2>/tmp/rc.package.debug.log  # Redirect stderr to log
# ... rest of script ...
```

### 5. Graceful Degradation

Handle missing resources gracefully:

```javascript
// Try external path first, fall back to standard
let basePath = '/mod/external/usr/mww/package';
if (!await pathExists(basePath)) {
	basePath = '/usr/mww/package';
}
```

```bash
# Check multiple possible locations
for dir in "/mod/external/usr/mww/package" "/usr/mww/package"; do
	if [ -d "$dir" ]; then
		PACKAGE_DIR="$dir"
		break
	fi
done
```

### 6. User Data Preservation

- Never delete user configs - rename with timestamp
- Create backups before overwrite
- Provide "Load Template" separate from "Load File"
- Confirm destructive actions

### 7. Async Boot, Sync Manual

```bash
case $1 in
	""|load)
		# Boot: check CONFIG_WAIT to decide sync vs async
		if [ "$wait_time" = "0" ]; then
			# Sync start when no wait needed
			start_daemon "$basedir" || exit 1
		else
			# Async with resource waits
			( start_async "$basedir" "$wait_time" ) &
		fi
		;;
	start)
		# Manual: immediate feedback, fail fast
		check_resources || exit 1
		start_daemon || exit 1
		;;
esac
```

### 8. Test Deployment Scripts

Create rapid test cycle:

1. Edit source files
2. Run `./deploy-package.sh` (seconds)
3. Test in browser
4. Check logs
5. Iterate

No need for full `make` rebuild during development.

### 9. Document Deployment Paths

In README or Config.in, document:
- Web interface URL
- Config file locations
- Log file locations
- Template file locations
- Auto-detection behavior

### 10. Version Control .template Files

Templates should be in repository:
```
make/pkgs/package/files/root/
├── mod/etc/default.package/
│   └── package.rc.template  ← In git
└── usr/mww/package/conf/
    ├── config.php.template  ← In git
    └── access.ini.template  ← In git
```

Runtime configs excluded via `.gitignore`:
```
# .gitignore
*.cfg
!*.template
```

---

## Advanced Patterns

### Base Directory UX: Storage Chooser

For packages requiring installation to user storage (USB, NAS), provide an interactive path chooser:

```javascript
// In CGI or editor HTML
async function loadMountPoints() {
    // Fetch mount points from backend
    const response = await fetch('/cgi-bin/conf/package?ajax=1&action=get_storage');
    const data = await parseJSON(response);
    
    const chooser = document.getElementById('storageChooser');
    chooser.innerHTML = '<option value="">Select storage device...</option>';
    
    data.mountpoints.forEach(mp => {
        // Show: /var/media/ftp/USB_STICK_01 (ext4, 128GB free)
        const option = document.createElement('option');
        option.value = mp.path;
        option.textContent = `${mp.path} (${mp.fstype}, ${mp.free_space} free)`;
        chooser.appendChild(option);
    });
}

function selectStorage(path) {
    // Append package-specific subdirectory
    const basedir = `${path}/package`;
    document.getElementById('basedir').value = basedir;
    
    // Show recommendation
    const fstype = path.dataset.fstype;
    if (fstype !== 'ext4' && fstype !== 'ext3') {
        showWarning(`${fstype} not recommended. Consider formatting as ext4 for best performance.`);
    }
}
```

**Backend implementation** (in CGI):

```bash
get_storage)
    echo '{'
    echo '  "mountpoints": ['
    
    # List mounted filesystems
    df -hT | grep "^/dev/" | while read -r line; do
        DEVICE=$(echo "$line" | awk '{print $1}')
        FSTYPE=$(echo "$line" | awk '{print $2}')
        SIZE=$(echo "$line" | awk '{print $3}')
        USED=$(echo "$line" | awk '{print $4}')
        AVAIL=$(echo "$line" | awk '{print $5}')
        MOUNT=$(echo "$line" | awk '{print $7}')
        
        # Only include /var/media/ftp/* mounts
        case "$MOUNT" in
            /var/media/ftp/*)
                echo "    {"
                echo "      \"path\": \"$MOUNT\","
                echo "      \"fstype\": \"$FSTYPE\","
                echo "      \"free_space\": \"$AVAIL\""
                echo "    },"
                ;;
        esac
    done | sed '$ s/,$//'  # Remove trailing comma from last item
    
    echo '  ]'
    echo '}'
    ;;
```

**Key principles:**
- Always suggest package-specific subdirectory (`/path/package`, not just `/path`)
- Show filesystem type and free space
- Warn about non-ext4 filesystems
- Include subdirectories under `/var/media/ftp/` if users commonly store data there

### Wizard Design Patterns

For packages with complex initial setup, implement setup wizards that:

#### 1. Keep config editable even during wizard

```javascript
// WRONG - lock all inputs during wizard
if (wizardActive) {
    document.querySelectorAll('input').forEach(el => el.disabled = true);
}

// CORRECT - keep critical fields editable
if (wizardActive) {
    // User may need to change base directory even during setup
    document.getElementById('basedir').disabled = false;
    document.getElementById('storageChooser').hidden = false;
}
```

#### 2. Default to existing config when present

```javascript
function initWizard() {
    // Load saved config first
    const savedBasedir = getCachedConfig('BASEDIR');
    
    if (savedBasedir) {
        // Pre-fill with existing value (even if path doesn't exist yet)
        document.getElementById('basedir').value = savedBasedir;
    } else {
        // Show wizard to select new path
        showStorageChooser();
    }
}
```

#### 3. Footer-Based Confirmation Pattern

**CRITICAL**: Don't create separate modals for wizard exit confirmation - use inline footer state changes:

```html
<!-- Wizard structure -->
<div id="setupWizardModal" class="modal">
    <div class="modal-content">
        <div class="modal-header">
            <h2>Initial Setup Wizard</h2>
            <button class="close" onclick="closeSetupWizard()">&times;</button>
        </div>
        
        <div class="modal-body">
            <!-- Wizard content here -->
        </div>
        
        <!-- Footer with two states -->
        <div id="wizardFooter" class="modal-footer">
            <!-- Normal navigation state -->
            <div id="wizardFooterNormal">
                <button onclick="closeSetupWizard()">Cancel</button>
                <button onclick="wizardPrev()" id="btnWizPrev">Back</button>
                <button onclick="wizardNext()" id="btnWizNext">Next</button>
            </div>
            
            <!-- Confirmation state (hidden by default) -->
            <div id="wizardFooterConfirm" style="display: none;">
                <p style="margin: 0 auto; color: #856404;">⚠ Exit wizard? Unsaved changes will be lost.</p>
                <div style="display: flex; gap: 10px;">
                    <button onclick="cancelCloseWizard()">Cancel</button>
                    <button onclick="confirmCloseWizard()" style="background: #dc3545;">Exit</button>
                </div>
            </div>
        </div>
    </div>
</div>
```

```javascript
// Wizard state management
function closeSetupWizard() {
    // Show confirmation in footer (not separate modal)
    document.getElementById('wizardFooterNormal').style.display = 'none';
    document.getElementById('wizardFooterConfirm').style.display = 'flex';
}

function cancelCloseWizard() {
    // Return to normal footer
    document.getElementById('wizardFooterConfirm').style.display = 'none';
    document.getElementById('wizardFooterNormal').style.display = 'block';
}

function confirmCloseWizard() {
    // Actually close wizard
    const wizardModal = document.getElementById('setupWizardModal');
    wizardModal.style.display = 'none';
    
    // Reset footer state
    document.getElementById('wizardFooterConfirm').style.display = 'none';
    document.getElementById('wizardFooterNormal').style.display = 'block';
}

// ESC key handling for wizard
let wizardEscHandler = null;

function showSetupWizard() {
    const wizardModal = document.getElementById('setupWizardModal');
    wizardModal.style.display = 'block';
    
    // Setup ESC key handler
    wizardEscHandler = (e) => {
        if (e.key !== 'Escape') return;
        
        const confirmVisible = document.getElementById('wizardFooterConfirm').style.display !== 'none';
        
        if (confirmVisible) {
            // ESC when confirmation showing = cancel confirmation
            cancelCloseWizard();
        } else {
            // ESC when wizard showing = show confirmation
            closeSetupWizard();
        }
    };
    
    document.addEventListener('keydown', wizardEscHandler);
}

function hideWizard() {
    document.getElementById('setupWizardModal').style.display = 'none';
    
    // Remove ESC handler
    if (wizardEscHandler) {
        document.removeEventListener('keydown', wizardEscHandler);
        wizardEscHandler = null;
    }
}
```

**Why footer-based confirmation?**
- No z-index conflicts with wizard modal
- No separate overlay management
- Cleaner UX - confirmation is contextual
- ESC key behavior is intuitive (toggle confirmation state)

### Editor Advanced Patterns

#### 1. Comprehensive Tooltip System

Every toolbar control needs localized tooltips:

```javascript
const tooltips = {
    en: {
        btnLoadTemplate: "Load default template (replaces current content)",
        btnReload: "Reload file from server (discards unsaved changes)",
        btnLoadFile: "Load configuration file from disk",
        btnSave: "Save current configuration to server",
        btnDownload: "Download configuration file",
        btnValidate: "Check configuration syntax",
        btnHistory: "View save history and restore previous versions",
        btnRestore: "Restore from backup",
        langSelector: "Change interface language"
    },
    de: { /* German translations */ },
    it: { /* Italian translations */ },
    fr: { /* French translations */ },
    es: { /* Spanish translations */ }
};

function applyTooltips(lang) {
    const t = tooltips[lang];
    document.getElementById('btnLoadTemplate').title = t.btnLoadTemplate;
    document.getElementById('btnReload').title = t.btnReload;
    document.getElementById('btnLoadFile').title = t.btnLoadFile;
    document.getElementById('btnSave').title = t.btnSave;
    document.getElementById('btnDownload').title = t.btnDownload;
    document.getElementById('btnValidate').title = t.btnValidate;
    document.getElementById('btnHistory').title = t.btnHistory;
    document.getElementById('btnRestore').title = t.btnRestore;
    document.getElementById('langSelector').title = t.langSelector;
}
```

#### 2. Promise-Based Confirmation Modal

**Use custom modals instead of alert()/confirm()** for better UX:

```javascript
// Generic confirmation modal with Promise
function showConfirmModal(title, message) {
    return new Promise((resolve) => {
        const modal = document.getElementById('confirmModal');
        const titleEl = document.getElementById('confirmTitle');
        const messageEl = document.getElementById('confirmMessage');
        const okBtn = document.getElementById('confirmOk');
        const cancelBtn = document.getElementById('confirmCancel');
        const closeBtn = document.querySelector('#confirmModal .close');
        
        // Set content
        titleEl.textContent = title;
        messageEl.textContent = message;
        modal.style.display = 'block';
        
        // Cleanup function
        const cleanup = () => {
            modal.style.display = 'none';
            okBtn.onclick = null;
            cancelBtn.onclick = null;
            closeBtn.onclick = null;
            document.removeEventListener('keydown', escHandler);
        };
        
        // Button handlers
        okBtn.onclick = () => {
            cleanup();
            resolve(true);
        };
        
        cancelBtn.onclick = closeBtn.onclick = () => {
            cleanup();
            resolve(false);
        };
        
        // ESC key handler
        const escHandler = (e) => {
            if (e.key === 'Escape' && modal.style.display === 'block') {
                cleanup();
                resolve(false);
            }
        };
        document.addEventListener('keydown', escHandler);
    });
}

// Usage example
async function loadTemplate() {
    const confirmed = await showConfirmModal(
        'Load Template',
        'This will replace your current configuration. Continue?'
    );
    
    if (!confirmed) return;
    
    // Load template...
}
```

```html
<!-- Confirmation modal HTML -->
<div id="confirmModal" class="modal">
    <div class="modal-content" style="max-width: 400px;">
        <div class="modal-header">
            <h3 id="confirmTitle">Confirm</h3>
            <span class="close">&times;</span>
        </div>
        <div class="modal-body">
            <p id="confirmMessage"></p>
        </div>
        <div class="modal-footer">
            <button id="confirmCancel" class="btn-secondary">Cancel</button>
            <button id="confirmOk" class="btn-primary">OK</button>
        </div>
    </div>
</div>
```

**Benefits:**
- async/await syntax
- No callback hell
- Reusable for all confirmations
- ESC key support
- Clean cleanup

#### 3. History Modal with ESC Support

```javascript
function showHistory() {
    const modal = document.getElementById('historyModal');
    modal.style.display = 'block';
    
    // Load backup files
    loadBackupList();
    
    // ESC to close
    document.addEventListener('keydown', handleHistoryEsc);
}

function handleHistoryEsc(e) {
    if (e.key === 'Escape') {
        closeHistory();
    }
}

function closeHistory() {
    document.getElementById('historyModal').style.display = 'none';
    document.removeEventListener('keydown', handleHistoryEsc);
}
```

#### 4. Context-Aware Validation

```javascript
function validateLine(line, lineNum) {
    const trimmed = line.trim();
    
    // Skip comments
    if (trimmed.startsWith('#')) {
        return { valid: true };
    }
    
    // Skip empty lines
    if (trimmed === '') {
        return { valid: true };
    }
    
    // Parse command = value
    const match = trimmed.match(/^(\w+)\s*=\s*(.*)$/);
    if (!match) {
        return { valid: false, error: `Line ${lineNum}: Invalid syntax (expected: command = value)` };
    }
    
    const [, command, value] = match;
    
    // Context-aware validation by command type
    switch (command) {
        case 'scgi_port':
            return validateSCGIPort(value, lineNum);
        
        case 'bind':
            return validateIP(value, lineNum, true);  // Allow 0.0.0.0
        
        case 'ip':
            return validateIP(value, lineNum, false);  // Standard IPs only
        
        case 'max_memory_usage':
            return validateSize(value, lineNum);  // Allow 16M, 512K, etc.
        
        case 'download_rate':
        case 'upload_rate':
            return validateRate(value, lineNum);  // Allow 0 (unlimited)
        
        default:
            // Unknown command - accept but mark as unknown
            return { valid: true, unknown: command };
    }
}

function validateSCGIPort(value, lineNum) {
    // Accept various formats:
    // - 127.0.0.1:5000
    // - localhost:5000
    // - :5000
    // - 5000
    if (/^((\d{1,3}\.){3}\d{1,3}|localhost)?:?\d{1,5}$/.test(value)) {
        return { valid: true };
    }
    return { valid: false, error: `Line ${lineNum}: Invalid SCGI port format` };
}

function validateSize(value, lineNum) {
    // Accept: 16M, 512K, 1G, or plain numbers
    if (/^\d+[KMG]?$/.test(value)) {
        return { valid: true };
    }
    return { valid: false, error: `Line ${lineNum}: Invalid size format (use 16M, 512K, etc.)` };
}
```

#### 5. Selection Visibility with Error Highlighting

```css
/* Ensure selection remains visible on top of error markers */
.ace_selection {
    background: rgba(100, 150, 255, 0.3) !important;
    z-index: 10;
}

/* Error markers should not obscure text */
.ace_error-line {
    background: rgba(255, 0, 0, 0.1);
    position: absolute;
    z-index: 1;
}

/* Selected text must be readable */
.ace_selected-word {
    background: rgba(100, 150, 255, 0.2);
    border: 1px solid rgba(100, 150, 255, 0.5);
}

/* Don't use reverse video that hides text */
.ace_active-line {
    background: rgba(0, 0, 0, 0.05) !important;
}
```

---

## Debug Playbook

### Systematic Troubleshooting for "Config Not Saving"

When configuration values don't save or apply correctly, follow this checklist:

#### Step 1: Verify Variable Registration

```bash
# Check if modconf sees the variable
modconf vars <package>

# Expected: Variable appears in list
# If NOT listed → problem with default cfg

# Check default config exists and is deployed
cat /mod/etc/default.<package>/<package>.cfg

# Look for export statement
grep "^export.*<VARNAME>" /mod/etc/default.<package>/<package>.cfg

# If missing export → add it and redeploy
```

#### Step 2: Check Form Field Naming

```bash
# In CGI file, find the form field:
grep "name=['\"]fieldname['\"]" /usr/lib/cgi-bin/<package>.cgi

# Verify naming convention matches:
# Form field "basedir" should map to <PKG>_BASEDIR
# Form field "enabled" should map to <PKG>_ENABLED

# Check if variable uses expected naming pattern
modconf vars <package> | grep "_BASEDIR"
```

#### Step 3: Verify Saved Config

```bash
# After clicking "Save" in web UI, check saved config
cat /mod/etc/conf/<package>.cfg

# Should contain:
export PACKAGE_VARNAME='new_value'

# If file doesn't exist → framework didn't save
# If wrong value → form field naming mismatch
# If empty → check previous steps
```

#### Step 4: Test Save Hook Execution

Add temporary logging to save hook:

```bash
#!/bin/sh

pkg_apply_save() {
    # Add debug logging
    exec 2>>/tmp/<package>-save-debug.log
    set -x
    
    echo "=== pkg_apply_save called at $(date) ===" >&2
    
    # Source config and log values
    [ -r /mod/etc/conf/<package>.cfg ] && . /mod/etc/conf/<package>.cfg
    
    echo "PACKAGE_BASEDIR=$PACKAGE_BASEDIR" >&2
    echo "PACKAGE_ENABLED=$PACKAGE_ENABLED" >&2
    
    # Your update logic here
    update_runtime_config
    
    echo "=== Update completed ===" >&2
    set +x
}
```

Then check logs after save:

```bash
cat /tmp/<package>-save-debug.log
```

#### Step 5: Verify Runtime File Updates

```bash
# If save hook should update runtime files (e.g., .rc, .conf)
# Check if file was actually modified

# Get last modification time
ls -la /path/to/runtime/.config.rc

# Verify content contains new values
grep "new_value" /path/to/runtime/.config.rc

# If not updated:
# - Check if pkg_apply_save() is called (add logging)
# - Check if file path is correct
# - Check file permissions
```

#### Step 6: Check Hook Timing Issues

```bash
# Verify save hook is reading from saved config, not stale values

# In /mod/etc/default.<package>/<package>.save:
pkg_apply_save() {
    # MUST re-source saved config to get new values
    [ -r /mod/etc/conf/<package>.cfg ] && . /mod/etc/conf/<package>.cfg
    
    # Log what values we see
    echo "Values loaded in pkg_apply_save:" >&2
    echo "  BASEDIR=$PACKAGE_BASEDIR" >&2
    
    # Update runtime config with these values
    update_config "$PACKAGE_BASEDIR"
}
```

### Debug Playbook for "Daemon Not Starting"

#### Step 1: Check Service Status

```bash
# Check if daemon is running
/etc/init.d/rc.<package> status

# Try manual start with verbose output
/etc/init.d/rc.<package> start

# Check process list
ps | grep package
pgrep -x package_binary
```

#### Step 2: Check Boot Logs

```bash
# If daemon should start at boot but doesn't:
cat /tmp/rc.<package>.log

# Look for:
# - "base directory not configured"
# - "directory not accessible"
# - "time not synchronized"
# - "failed to start"
```

#### Step 3: Verify Configuration

```bash
# Check enabled flag
cat /mod/etc/conf/<package>.cfg | grep ENABLED

# Check base directory
cat /mod/etc/conf/<package>.cfg | grep BASEDIR

# Verify directory exists
ls -la /path/to/basedir

# Check directory permissions
stat /path/to/basedir
```

#### Step 4: Test Async Boot Conditions

```bash
# If using async boot start, check wait conditions
# Time sync check:
date
# Should show current year (2025+), not 1970

# Directory availability:
df -h | grep /var/media/ftp
mount | grep /var/media/ftp

# If USB not mounted yet, check mount events
dmesg | tail -50
```

#### Step 5: Test Manual Start

```bash
# Source configuration manually and try to start
. /mod/etc/conf/<package>.cfg

# Check variables loaded
echo "ENABLED=$PACKAGE_ENABLED"
echo "BASEDIR=$PACKAGE_BASEDIR"

# Try starting daemon directly
/etc/init.d/rc.<package> start

# Check errors
echo $?
```

#### Step 6: Check Init Script Bugs

Common init script problems:

```bash
# 1. local keyword bug in case statement
# Look for patterns like:
case $1 in
    load)
        local basedir="$PACKAGE_BASEDIR"  # BUG! May be empty
        
# Fix: Remove local keyword
case $1 in
    load)
        basedir="$PACKAGE_BASEDIR"  # Correct

# 2. Missing background & for async start
case $1 in
    load)
        start_daemon "$basedir"  # BUG! Blocks boot
        
# Fix: Launch in background
case $1 in
    load)
        ( start_async "$basedir" ) &  # Correct

# 3. Not re-sourcing config in subshell
( 
    # BUG! Variables empty in subshell
    start_async "$basedir"
) &

# Fix: Re-source config in subshell
(
    . /etc/init.d/modlibrc
    [ -r /mod/etc/conf/<package>.cfg ] && . /mod/etc/conf/<package>.cfg
    start_async "$basedir"
) &
```

### Debug Playbook for "AJAX/CGI Errors"

#### Step 1: Check CGI Accessibility

```bash
# Verify CGI exists and is executable
ls -la /usr/lib/cgi-bin/<package>.cgi

# Check permissions (must be executable)
chmod +x /usr/lib/cgi-bin/<package>.cgi

# Test CGI access from browser console
fetch('/cgi-bin/<package>.cgi?ajax=1&action=test')
    .then(r => r.text())
    .then(console.log)
```

#### Step 2: Check AJAX Response Format

```javascript
// freetz-ng CGI returns HTML-wrapped JSON
// Verify response structure:
const response = await fetch('/cgi-bin/package.cgi?ajax=1&action=read');
const text = await response.text();
console.log(text);

// Should contain:
// <div class="ajax-json-box">...
// Content-Type: application/json
// {"success": true, ...}
// </pre></div></div>

// If plain JSON → wrong response format
// If HTML form → AJAX mode not detected
```

#### Step 3: Check Security Whitelist

```bash
# If getting "Access denied" errors
# Check CGI whitelist for file path

# In <package>.cgi, find read_file action:
case "$ACTION" in
    read_file)
        # Check if path is in whitelist
        case "$FILE_PATH" in
            /allowed/path/*|\
            /another/path/*)
                ALLOWED=1
                ;;
        esac
```

#### Step 4: Test with curl

```bash
# Test AJAX endpoint directly
curl 'http://fritz.box/cgi-bin/package.cgi?ajax=1&action=read_file&file=/test/path'

# Check response format
# Check error messages
# Verify JSON structure
```

#### Step 5: Check CGI Logs

```bash
# Add logging to CGI for debugging
# In <package>.cgi AJAX handler:
if [ "$AJAX_MODE" = "1" ]; then
    # Log request
    echo "$(date): AJAX request - action=$ACTION file=$FILE_PATH" >> /tmp/cgi-debug.log
    
    # Your handler...
    
    # Log result
    echo "$(date): Result - success=$SUCCESS" >> /tmp/cgi-debug.log
fi

# Check logs
tail -f /tmp/cgi-debug.log
```

### Debug Playbook for "Editor Not Loading/Saving"

#### Step 1: Check JavaScript Console

```javascript
// Open browser DevTools (F12)
// Check Console for errors:
// - Fetch failures
// - JSON parsing errors
// - Undefined functions
// - CORS issues
```

#### Step 2: Verify Template Paths

```bash
# Check template file exists
ls -la /mod/etc/default.<package>/<package>.rc.template
ls -la /usr/mww/<package>/conf/*.template

# Check template permissions (should be readable)
stat /mod/etc/default.<package>/<package>.rc.template

# Test template loading from CGI
curl 'http://fritz.box/cgi-bin/package.cgi?ajax=1&action=read_file&file=/mod/etc/default.package/template.rc'
```

#### Step 3: Test Editor Functions

```javascript
// In browser console, test individual functions:

// Test file loading
loadFileFromServer();

// Test template loading
loadTemplate();

// Test save
saveFileToServer();

// Check what errors appear
```

#### Step 4: Verify ACE Editor

```javascript
// Check if ACE is loaded
console.log(typeof ace);  // Should be 'object'

// Check editor instance
console.log(editor);  // Should show ACE editor object

// If undefined → ACE not loaded
// Check: <script src="/ace/ace.js"></script>
```

#### Step 5: Check File Path Detection

```javascript
// Test path detection logic
console.log(isFritzBox());  // Should return true on FritzBox
console.log(getBasePath());  // Should return correct path
console.log(getFilePath());  // Should return expected file path

// Verify paths exist on device
```

### Complete Debug Session Example

```bash
# Problem: "Config not saving for rtorrent package"

# 1. Check variable registration
ssh root@fritz.box "modconf vars rtorrent"
# Output: RTORRENT_ENABLED, RTORRENT_BASEDIR, ...
# ✓ Variables registered

# 2. Check default config
ssh root@fritz.box "cat /mod/etc/default.rtorrent/rtorrent.cfg | grep BASEDIR"
# Output: export RTORRENT_BASEDIR='/var/media/ftp/rtorrent'
# ✓ Default config correct

# 3. Save value from web UI, then check saved config
ssh root@fritz.box "cat /mod/etc/conf/rtorrent.cfg | grep BASEDIR"
# Output: export RTORRENT_BASEDIR='/tmp/test'
# ✓ Value saved correctly

# 4. Check if runtime file updated
ssh root@fritz.box "cat /var/media/ftp/rtorrent/.rtorrent.rc | grep scgi_port"
# Output: scgi_port = 127.0.0.1:5000  (old value!)
# ✗ Runtime file not updated!

# 5. Check save hook
ssh root@fritz.box "cat /mod/etc/default.rtorrent/rtorrent.save"
# Find: pkg_apply_save() updates .rtorrent.rc
# Add debug logging:

# (SSH to device)
cat > /tmp/debug-save.sh << 'EOF'
#!/bin/sh
pkg_apply_save() {
    exec 2>>/tmp/rtorrent-save-debug.log
    set -x
    echo "=== $(date) ==="
    [ -r /mod/etc/conf/rtorrent.cfg ] && . /mod/etc/conf/rtorrent.cfg
    echo "BASEDIR=$RTORRENT_BASEDIR"
    echo "PORT=$RTORRENT_PORT"
    # ... rest of function
}
EOF

# Append to actual save hook for testing
cat /tmp/debug-save.sh >> /mod/etc/default.rtorrent/rtorrent.save

# 6. Save again from web UI, check log
cat /tmp/rtorrent-save-debug.log
# Reveals: pkg_apply_save() not called!
# → Framework issue or wrong hook location

# 7. Verify save hook location and syntax
ls -la /mod/etc/default.rtorrent/rtorrent.save
# Check: executable, correct location

# 8. Check if framework finds the hook
# (Framework sources .save files from /mod/etc/default.<pkg>/)

# Resolution: Hook was in wrong location → moved to correct path → works
```

---

## Checklist for New Package

Use this checklist when creating a new freetz-ng package:

### Configuration Framework
- [ ] Created `/mod/etc/default.<package>/<package>.cfg` with all exports
- [ ] Created `/mod/etc/default.<package>/<package>.save` with hooks
- [ ] Verified `modconf vars <package>` lists all variables
- [ ] Tested that values persist across save/reload
- [ ] Documented system vs runtime pass-through variables
- [ ] Save hook uses `pkg_pre_save()` only for validation
- [ ] Save hook uses `pkg_apply_save()` for runtime file updates
- [ ] No implicit service restart on save

### Package Structure
- [ ] Created `make/pkgs/[package]/` directory
- [ ] Created `[package].mk` makefile
- [ ] Created `Config.in` with help text
- [ ] Created `files/.language` marker
- [ ] Created `files/root/` mirroring target filesystem

### CGI Script
- [ ] CGI script sources `/etc/init.d/modlibrc`
- [ ] Implements AJAX mode check (`ajax=1`)
- [ ] Returns HTML-wrapped JSON with marker
- [ ] Implements security whitelist
- [ ] Creates timestamped backups
- [ ] Handles basename expansion
- [ ] Language substitution via modlangsubst
- [ ] Form field names align with modconf variable naming

### Web Editor
- [ ] Uses ACE editor for syntax highlighting
- [ ] Multi-language translations object
- [ ] Auto-detects FritzBox environment
- [ ] Implements JSON parsing from HTML wrapper
- [ ] Load/Save/Template buttons
- [ ] Status feedback with auto-clear
- [ ] Confirmation prompts for destructive actions
- [ ] Error handling with graceful degradation
- [ ] Tooltips for all toolbar controls (localized)
- [ ] Validation ignores comment lines
- [ ] Selection visibility works with error highlighting

### Init Script
- [ ] Uses modlibrc and modlib functions
- [ ] Implements `is_running()` check
- [ ] Implements async boot start
- [ ] Implements wait conditions (time, directory)
- [ ] Avoids `local` in case statements
- [ ] Backgrounds boot start with `&`
- [ ] Re-sources config in subshell
- [ ] Uses `start-stop-daemon`
- [ ] Implements proper stop with timeout
- [ ] Logs to `/tmp/rc.[package].log`
- [ ] No phantom commands (only implements advertised commands)

### Templates
- [ ] Template files in `/mod/etc/default.[package]/`
- [ ] Template files in `/usr/mww/[package]/conf/`
- [ ] Makefile sets `chmod a+rw` for templates
- [ ] Templates added to CGI whitelist
- [ ] Web editor can load templates
- [ ] Templates separated from runtime configs

### Deployment
- [ ] Created `deploy-[package].sh` script
- [ ] Script processes language substitution
- [ ] Script deploys all components
- [ ] Script deploys templates with permissions
- [ ] Script deploys default config and save hooks
- [ ] Script verifies `modconf vars` after deployment
- [ ] Script gives completion feedback

### Documentation
- [ ] Config.in has clear help text
- [ ] URLs documented (web interface, CGI)
- [ ] File locations documented
- [ ] README with deployment instructions
- [ ] Changelog entries
- [ ] System vs runtime variables documented in default cfg

### Testing ("Done Definition")
- [ ] `modconf vars <package>` lists every UI-saved variable
- [ ] Values persist across reboot (`/mod/etc/conf/<package>.cfg`)
- [ ] Runtime config generation consistent with saved cfg
- [ ] Tested fresh install
- [ ] Tested template loading
- [ ] Tested save with backup
- [ ] Tested delete (rename) functionality
- [ ] Tested boot autostart after reboot
- [ ] Tested manual start/stop/restart
- [ ] Tested with external vs standard paths
- [ ] Checked logs for errors
- [ ] No implicit restarts on Save unless explicit
- [ ] Base directory chooser shows correct defaults (if applicable)
- [ ] Destructive editor actions require confirmation
- [ ] All tooltips and translations complete

---

## Example Package Structure

**Visual overview of a complete package with CGI + config + wizard:**

```
make/pkgs/package-cgi/
├── Config.in                              # Package options and help text
├── package-cgi.mk                         # Build rules and install targets
├── files/
│   ├── .language                          # Language marker
│   └── root/                              # Mirrors target filesystem
│       ├── etc/
│       │   ├── init.d/
│       │   │   └── rc.package             # Init script (async boot, modlib)
│       │   └── default.package/
│       │       ├── package.cfg            # Default system config (exports)
│       │       ├── package.save           # Save hooks (pre_save/apply_save)
│       │       └── app.rc.template        # Runtime config template
│       └── usr/
│           ├── lib/
│           │   └── cgi-bin/
│           │       └── package.cgi        # CGI backend (AJAX actions)
│           └── mww/
│               └── package/
│                   ├── index.html         # Main UI (with setup wizard)
│                   ├── app_config_editor.html  # Runtime config editor
│                   └── conf/
│                       ├── config.php.template    # Web interface config
│                       └── plugins.ini.template   # Plugin config
└── patches/                               # Source patches (if needed)

# In workspace root:
deploy-package-cgi.sh                      # Deployment script (dev iteration)
```

**Key file responsibilities:**

- **Config.in**: User-facing options, help text with URLs
- **.mk**: Installation rules, permissions, dependencies
- **rc.package**: Daemon lifecycle (async boot, wait conditions)
- **package.cfg**: System variables (ENABLED, BASEDIR, NICE) - exported
- **package.save**: Hooks for config save (validation, runtime file updates)
- **package.cgi**: AJAX backend (file read/write, whitelists, backups)
- **index.html**: Main UI with wizard, storage chooser, status
- **app_config_editor.html**: ACE editor for runtime configs
- **conf/*.template**: Default configs for first-time setup
- **deploy-package-cgi.sh**: Rapid deployment without full rebuild

**Data flow:**
```
User edits form → Submit
    ↓
Framework reads POST data
    ↓
Framework calls pkg_pre_save() [validation only]
    ↓
Framework saves to /mod/etc/conf/package.cfg
    ↓
Framework calls pkg_apply_save() [update runtime files]
    ↓
modsave persists to flash
    ↓
Init script reads /mod/etc/conf/package.cfg on boot
    ↓
Daemon starts with runtime config from basedir/.app.rc
```

---

## Quick Reference Card

### Most Common Debug Commands

```bash
# Check variable registration
modconf vars <package>

# Check default config
cat /mod/etc/default.<package>/<package>.cfg

# Check saved config
cat /mod/etc/conf/<package>.cfg

# Check if daemon running
/etc/init.d/rc.<package> status
ps | grep <package>

# Check boot logs
cat /tmp/rc.<package>.log

# Test AJAX endpoint
curl 'http://fritz.box/cgi-bin/<package>.cgi?ajax=1&action=test'

# Check CGI permissions
ls -la /usr/lib/cgi-bin/<package>.cgi

# Check template files
ls -la /mod/etc/default.<package>/*.template
ls -la /usr/mww/<package>/conf/*.template

# Manual save test
modconf set <package> ENABLED=yes BASEDIR=/tmp/test
modconf save <package>

# Check mount points
df -hT | grep /var/media/ftp

# Check time sync
date  # Should show 2025+, not 1970
```

### Most Critical Patterns

1. **Export all variables**: `export PACKAGE_VAR='value'` in default.cfg
2. **Hook timing**: Update runtime files in `pkg_apply_save()`, not `pkg_pre_save()`
3. **Form field naming**: `name="basedir"` → `PACKAGE_BASEDIR`
4. **No `local` in case statements**: Use plain assignment
5. **Async boot**: `( start_async ) &` to not block boot
6. **HTML-wrapped JSON**: Parse with text extraction, not `.json()`
7. **Timestamped backups**: `file.YYYY-MM-DD-HH-MM-SS`
8. **Template paths**: `/mod/etc/` not `/etc/`

---

## References

### Key Files to Study

For real-world examples, examine these packages in freetz-ng:

1. **rtorrent-cgi**: Complete CGI + web editor + init script example
   - `make/pkgs/rtorrent-cgi/`
   - Complex multi-file editor
   - Async boot start
   - Template system

2. **transmission**: Daemon package with web interface
   - `make/pkgs/transmission/`
   - Download management
   - Web UI integration

3. **mod**: Core modlib functions
   - `make/pkgs/mod/files/root/usr/lib/mww/`
   - CGI framework (`libmodcgi.sh`)
   - Common patterns

### External Resources

- freetz-ng Wiki: https://ircama.github.io/freetz-evo/
- modlibrc functions: `tools/freetz_functions`
- ACE Editor: https://ace.c9.io/
- FritzBox API: AVM documentation

---

## Conclusion

This guide captures patterns and solutions from real package development. When developing new packages:

1. **Follow established patterns** - Don't reinvent
2. **Security first** - Whitelist, validate, backup
3. **Async boot** - Never block boot sequence
4. **User-friendly** - Multilingual, error messages, confirmations
5. **Iterate quickly** - Use deployment scripts
6. **Log everything** - Future debugging will thank you
7. **Test edge cases** - External paths, missing files, boot scenarios

The most critical lesson: **freetz-ng has unique requirements** (HTML-wrapped JSON, .mod paths, async boot) that differ from standard Linux development. Understanding these patterns avoids hours of debugging.
