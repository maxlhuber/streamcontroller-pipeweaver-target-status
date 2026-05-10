# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog and this project follows Semantic Versioning as far as practical for a small plugin.

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
