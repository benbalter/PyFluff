# PyFluff Scripts

This directory contains utility scripts for PyFluff development and maintenance.

## generate_actions_js.py

Generates `web/actions.js` from `docs/actionlist.md`.

**Usage:**
```bash
python scripts/generate_actions_js.py
```

This script parses the markdown action list and creates a JavaScript array with all 1400+ Furby Connect actions, making them searchable in the web interface.

**When to run:**
- After updating `docs/actionlist.md` with new actions
- When the action format changes
- If `web/actions.js` becomes corrupted

**Output:**
- `web/actions.js` - Complete action database with search functionality
- Console output showing statistics about parsed actions

The generated file includes:
- All action definitions with input, index, subindex, specific values
- Category and description for each action
- Cookie management for recent actions
- Search and dropdown UI logic

## test_f2f_connection.py

Diagnostic tool for testing connections to Furbies in F2F (Furby-to-Furby) mode.

**Usage:**
```bash
# Normal diagnostic test
python scripts/test_f2f_connection.py AA:BB:CC:DD:EE:FF

# Aggressive mode with more retries
python scripts/test_f2f_connection.py AA:BB:CC:DD:EE:FF --aggressive
```

**What it tests:**
1. **BLE Scanning**: Verifies Bluetooth is working and can discover devices
2. **Direct Connection**: Tests connection to specific Furby by MAC address
3. **Communication**: Validates commands work (device info, antenna control)

**Modes:**
- **Normal**: 3 retries with 15s timeout per attempt (45s total)
- **Aggressive**: 10 retries with 20s timeout per attempt (200s total)

**When to use:**
- Furby won't connect in F2F mode
- Debugging connection issues
- Verifying MAC address is correct
- Testing after Bluetooth configuration changes
- Troubleshooting range or interference problems

**Output:**
- Colored diagnostic messages
- List of discovered BLE devices
- Connection attempt progress
- Device information if successful
- Detailed troubleshooting tips if failed

## create_copilot_dlc.py

Documentation and guide for creating custom DLC files with the GitHub Copilot logo.

**Usage:**
```bash
python scripts/create_copilot_dlc.py
```

**What it provides:**
- Comprehensive guide to DLC file creation
- Documentation on Furby's DLC format
- Instructions for uploading DLC files
- Links to relevant resources and tools

**Purpose:**
This script serves as documentation rather than a working DLC generator. Creating
functional Furby DLC files requires understanding the proprietary format, including:
- GeneralPlus A1800 audio codec
- Furby's custom 64-color LCD palette
- Action sequence definitions
- Proper file structure

**Current capabilities:**
✓ Explains the DLC creation process
✓ Documents upload procedures via CLI, API, and Web UI
✓ Provides community resources
✓ Outlines requirements for DLC generation

**To upload existing DLC files:**
```bash
# Via CLI
python -m pyfluff.cli upload-dlc file.dlc --slot 2
python -m pyfluff.cli load-dlc 2
python -m pyfluff.cli activate-dlc

# Via Web UI  
python -m pyfluff.server
# Then open http://localhost:8080 and use DLC Management section
```

**Contributing:**
If you're interested in reverse engineering the DLC format or creating DLC
generation tools, see the guide for information on how to contribute!
