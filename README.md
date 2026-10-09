# BombSquad Test Plugin

A minimal, safe BombSquad API 9 plugin starter.

## What it does

- Declares the required Ballistica API version (9).
- Exports a `babase.Plugin` subclass with verified metadata.
- Shows a small on-screen message when the app reaches the running state.

## Installation

### Manual Installation

1. Locate your BombSquad configuration directory:
   - **Windows:** `%APPDATA%/BombSquad` or `C:\Users\<YourUser>\AppData\Roaming\BombSquad`
   - **macOS:** `~/Library/Application Support/BombSquad`
   - **Linux:** `~/.config/bombsquad` or `~/.bombsquad`

2. Navigate to (or create) the `mods` subdirectory within that config directory.

3. Download or place `test_plugin.py` into that `mods` directory:
   ```
   <config-dir>/mods/test_plugin.py
   ```

4. Restart BombSquad or reload the plugin system. The plugin will be auto-discovered and auto-enabled (by default).

5. Look for the on-screen message: **"Test Plugin Loaded"** (green text) when BombSquad finishes starting up.

### Automated Install (via Dev Console)

If you have BombSquad open with developer console access, you can paste this into the console to download and install:

```python
import urllib.request
import os

url = "https://raw.githubusercontent.com/sadra-funlife/bombsquad-test-plugin/main/test_plugin.py"
mods_dir = os.path.expanduser("~/.config/bombsquad/mods")  # Adjust for your OS
os.makedirs(mods_dir, exist_ok=True)
with urllib.request.urlopen(url) as response:
    with open(os.path.join(mods_dir, "test_plugin.py"), "wb") as f:
        f.write(response.read())
print("Plugin installed. Restart BombSquad to load it.")
```

(Adjust the `mods_dir` path for your OS as noted in the Manual Installation section.)

## Testing Status

**⚠️ In-game validation has not been performed in this environment.**

The plugin follows the verified API 9 metadata syntax and lifecycle patterns from the official Ballistica source code, but actual behavior in a running BombSquad instance has not been tested. If you encounter issues:

1. Verify the file is in the correct mods directory.
2. Check BombSquad's console or log output for any errors.
3. Ensure you are using BombSquad with API 9 support.
4. File an issue on this repository with the error message and your OS.

## Implementation Notes

- **No telemetry, credentials, or network access:** This plugin does nothing except show a message.
- **Minimal scope:** Intentionally kept small to serve as a template.
- **Verified against official source:** The metadata and plugin lifecycle are confirmed from https://github.com/efroemling/ballistica.

## Documentation References

- [Ballistica Docs](https://www.ballistica.net/docs)
- [Ballistica API 9 Reference](https://ballistica.net/apidocs/api9/)
- [BombSquad Modding Guide](https://www.froemling.net/docs/bombsquad-modding-guide)

## License

MIT License – see [LICENSE](LICENSE) for details.
