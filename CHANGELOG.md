# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog and this project follows Semantic Versioning as far as practical for a small plugin.

## [0.2.0] - 2026-05-11

### Fixed
- Eliminated double HTTP request per toggle/tick — `_get_current_target` now
  accepts pre-fetched API data instead of fetching internally, halving API
  load and removing a race condition between the two responses
- Settings initialisation moved to `on_ready`; `_settings()` no longer writes
  to disk on every poll tick when nothing has changed
- Deep API JSON paths (`data["audio"]["profile"]...`) now guarded with
  descriptive `KeyError` → `RuntimeError` messages instead of crashing silently
- Removed dead poll-interval `SpinRow` from the config UI — it was visible
  but had no effect
- Replaced developer-specific PipeWire device node names as defaults with
  empty strings; button now shows "Configure" instead of "ERR" on first run
- All config-row subtitle strings are now English (were previously German
  while titles were English)
- Icon selection in `refresh_state` now uses `_match_text` (case-insensitive
  substring) consistently instead of raw equality comparisons

### Changed
- CI workflow now runs a `ruff` lint job on every push; ZIP build only runs
  on tag pushes and requires lint to pass

## [0.1.1] - 2026-05-10

### Added
- Initial public release
- Dynamic target status button for StreamController
- Speaker/headphone icon switching based on active PipeWeaver target
- Manual installation instructions in README

### Changed
- Switched plugin logic to the PipeWeaver HTTP API
- Improved compatibility with current PipeWeaver daemon JSON schema
- Removed hard dependency on fixed PipeWire node IDs for switching logic

### Fixed
- Repaired target status detection after PipeWeaver CLI/schema mismatch
- Repaired target switching on systems where `pipeweaver-client` command flow no longer worked reliably
