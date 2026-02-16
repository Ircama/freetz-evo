# Freetz Translate Cache Manager

**Desktop GUI for managing translation cache files**

## Features

### ✅ Professional UI
- **Sortable columns**: Click any column header to sort (click again to reverse)
- **Alternating row colors**: Better readability in large tables
- **Tabbed interface**: Clean separation of functions (Entry Editor, Bulk Operations, Test Translation)
- **Status bar**: Real-time feedback on operations

### 🔍 Advanced Filtering
- **Language**: Filter by target language (it, de, fr, es, etc.)
- **Agent**: Filter by translation service (deepl, mymemory, etc.)
- **GitHub user**: Filter by who created/modified entries
- **Date range**: Filter by timestamp period (with calendar picker if tkcalendar installed)
- **Metadata presence**: Show only entries without metadata (legacy entries)
- **Search**: Full-text search with three modes:
  - **Contains**: Simple substring search
  - **Wildcard**: Unix-style wildcards (`*`, `?`, `[]`)
  - **Regex**: Full regular expression support
- **Search scope**: Select where to search (key, original, translation)
- **Case sensitivity**: Toggle for search

### 📝 Single Entry Editor (Tab 1)
- View and edit individual entries
- Modify original text and translation
- Update metadata (timestamp, GitHub user)
- Delete single entry
- Auto-fills timestamp and user on save

### ⚡ Bulk Operations (Tab 2)
- **Text Replace**:
  - Find/replace in selected translations
  - Supports plain text and regex modes
  - Case-sensitive option
  - Auto-updates metadata on change
  
- **Metadata Update**:
  - Apply timestamp to all selected entries
  - Apply GitHub user to all selected entries
  - Quick buttons: "Now" (current timestamp), "Auto" (git user)
  
- **Bulk Delete**:
  - Remove multiple entries at once
  - Confirmation dialog for safety

### 🧪 Test Translation (Tab 3)
- Test translations with different agents **without polluting cache**
- Integrates with `freetz_translate` script
- Runs in background thread (non-blocking UI)
- Shows detailed output including debug info
- "Use from editor" button copies text from editor tab

### 💾 Data Management
- **Add new entry**: Create translations manually (button in toolbar)
- **Save all**: Writes changes to JSON files with automatic timestamped backups
- **Reload**: Refresh from disk (e.g., after external changes)
- **Dirty tracking**: Shows which language files have unsaved changes

### 🎨 Selection Tools
- **Multi-select**: Ctrl+Click, Shift+Click for multiple entries
- **Select visible**: Select all currently filtered entries at once
- **Clear selection**: Deselect all

## Installation

### Requirements
```bash
# Required
sudo apt-get install python3-tk

# Optional (for calendar widget)
pip3 install tkcalendar
```

## Usage

### Launch
```bash
# From tools directory (auto-detects translate_cache/)
cd tools
python3 translate_cache_manager.py

# Or specify custom cache directory
python3 translate_cache_manager.py --cache-dir /path/to/cache
```

### Typical Workflow

1. **Filter entries** you want to work on (e.g., agent=deepl, date range)
2. **Select visible** to select all filtered entries
3. Go to **Bulk Operations** tab:
   - Replace text patterns across all selected (e.g., fix typos)
   - Update metadata (e.g., add timestamp to legacy entries)
4. **Save all** to write changes with backups
5. **Test** translations with different agents before committing

### Keyboard Shortcuts
- **Ctrl+Click**: Add to selection
- **Shift+Click**: Select range
- **Click column header**: Sort by that column

## File Format

Cache files are JSON with this structure:
```json
{
  "deepl:Source text": {
    "original": "Source text",
    "translation": "Testo di origine",
    "timestamp": "2026-02-15T10:20:00Z",
    "github_user": "username",
    "service": "deepl"
  }
}
```

**Backward compatible**: Entries without metadata still load and work correctly.

## Backup Strategy

- Automatic timestamped backups before each save: `it.json.backup-20260215-102030`
- Old backups accumulate (manual cleanup recommended)
- Original cache file never modified until "Save all" clicked

## Testing Translation Agents

The Test Translation tab allows safe experimentation:
- **Cache disabled**: Test translations don't pollute production cache
- **All agents supported**: deepl, mymemory, libretranslate, apertium, lingva, openai
- **Real-time output**: See exact response from translation service
- **Debug info**: stderr output shows API calls and rate limiting

## Tips

### Find all entries without metadata
1. Check "Only without metadata"
2. Click "Apply filters"
3. Click "Select visible"
4. Go to Bulk Operations → Update metadata
5. Click "Now" and "Auto" buttons
6. Click "Apply metadata to selected"

### Fix bulk translation errors
1. Search for error pattern (e.g., regex `\berror\b`)
2. Select visible
3. Bulk replace with correct translation
4. Verify in editor tab
5. Save all

### Compare agent quality
1. Select an entry in editor
2. Click "Use from editor" in Test tab
3. Test with different agents
4. Compare results
5. Manually update translation if needed

### Add translations for new package
1. Click "Add entry" button
2. Fill fields (lang, agent, source, original, translation)
3. Click "Add"
4. Entry appears in table immediately
5. Save when ready

## Troubleshooting

### "tkinter is required"
Install python3-tk package on your system.

### "freetz_translate not found"
Test translation requires `freetz_translate` script in parent directory of cache.

### Date picker shows text entry instead of calendar
Install tkcalendar: `pip3 install tkcalendar`

### Changes not saved
Click "Save all" button (bottom right or toolbar).
Check status bar for confirm message.

### Sort not working
Click column header directly (not row).

## Advanced

### Regex Examples
- Find HTML tags: `<[^>]+>`
- Find escaped newlines: `\\n`
- Find URLs: `https?://[^\s]+`

### Wildcard Examples
- Match variations: `config*` (config, configuration, etc.)
- Match single char: `u?er` (user, uber, etc.)

### Bulk Operations
All bulk operations auto-update metadata (timestamp + user) on modified entries.

## Development

- **File**: `tools/translate_cache_manager.py`
- **Language**: Python 3.8+
- **UI Framework**: Tkinter (built-in)
- **Optional**: tkcalendar for date widgets
- **Threading**: Background translation tests (non-blocking)

## License

Same as freetz-ng project.
