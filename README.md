# PipeWeaver Target Status

A StreamController plugin that toggles a PipeWeaver output target between two physical devices and shows the active target with a dynamic icon.

## What it does

This plugin adds a button action for StreamController that:

- switches a PipeWeaver target such as `Master Channel`
- toggles between two physical output devices, e.g. speakers and headphones
- shows a speaker or headphone icon depending on the currently attached device
- falls back to an unknown icon when the active device cannot be identified

## Why this version exists

This plugin uses the PipeWeaver HTTP API directly:

- `GET /api/get-devices`
- `POST /api/command`

That makes it more robust on setups where the `pipeweaver-client` CLI status/edit path is broken or out of sync with the daemon JSON schema.

## Requirements

- StreamController `1.5.0-beta.12` or newer
- PipeWeaver daemon running locally
- PipeWeaver web/API endpoint reachable on:
  - `http://127.0.0.1:14565`
  - or `http://localhost:14565`

## Installation

### Manual

Copy this repository's plugin directory to your StreamController plugins directory:

```bash
cp -a ./ ~/.var/app/com.core447.StreamController/data/plugins/com_hubelix_PipeWeaverTargetStatus
```

Then restart StreamController.

## Configuration

The action exposes these settings:

- **PipeWeaver target name**
  - Usually something like `Master Channel`
- **Speaker device match**
  - Usually a PipeWire node name like `alsa_output.usb-bestechnic_EDIFIER_M60_20160406.1-00.analog-stereo`
- **Headphone device match**
  - Usually a PipeWire node name like `xlrdock-sink`

Matching is intentionally tolerant:

- exact node name works
- description substring matches also work

## Behavior

On press, the plugin:

1. reads the current PipeWeaver device state from `/api/get-devices`
2. resolves the configured master target
3. resolves speaker and headphone targets from the available physical targets
4. removes existing attached physical devices from the master target
5. attaches the selected next target via `/api/command`

## Notes

- The plugin is focused on a simple 2-target toggle workflow.
- It avoids hard dependency on fixed PipeWire node IDs.
- It is currently tailored for local PipeWeaver access, not remote API access.

## Roadmap

Possible future improvements:

- better multi-output handling
- configurable labels/icons
- packaged release artifacts for easier install/update

## Development

Useful files in this repository:

- `actions/TargetToggleAction/TargetToggleAction.py` - main plugin logic
- `manifest.json` - plugin metadata
- `main.py` - StreamController plugin registration
- `CHANGELOG.md` - release history

## License

MIT
