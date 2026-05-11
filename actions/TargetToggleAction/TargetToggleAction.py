import json
import os
import urllib.request
from typing import Optional, Tuple

import gi
from src.backend.PluginManager.ActionBase import ActionBase
from src.backend.DeckManagement.InputIdentifier import Input

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk


class TargetToggleAction(ActionBase):
    API_STATUS_URLS = [
        "http://127.0.0.1:14565/api/get-devices",
        "http://localhost:14565/api/get-devices",
    ]
    API_COMMAND_URLS = [
        "http://127.0.0.1:14565/api/command",
        "http://localhost:14565/api/command",
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.has_configuration = True
        self.current_icon: Optional[str] = None
        self.current_target_name: Optional[str] = None
        self.last_error: Optional[str] = None

    def on_ready(self):
        self._init_settings()
        self.refresh_state(force=True)

    def on_tick(self):
        self.refresh_state(force=False)

    def event_callback(self, event, data):
        if event == Input.Key.Events.SHORT_UP:
            try:
                self.toggle_target()
                self.refresh_state(force=True)
            except Exception as e:
                self._show_error(e)

    def _make_string_list(self, items: list[str]) -> Gtk.StringList:
        sl = Gtk.StringList()
        for item in items:
            sl.append(item)
        return sl

    def _combo_index(self, items: list[str], current: str) -> int:
        """Return index of current value in items, or 0 if not found."""
        try:
            return items.index(current)
        except ValueError:
            return 0

    def _fetch_device_options(self):
        """Return (target_names, device_names) from PipeWeaver API, or ([], []) on error."""
        try:
            data = self._get_status_data()
            physical = data["audio"]["profile"]["devices"]["targets"]["physical_devices"]
            target_names = [
                dev.get("description", {}).get("name") or dev.get("description", {}).get("id", "")
                for dev in physical
                if dev.get("description", {}).get("name") or dev.get("description", {}).get("id")
            ]
            raw_devices = data["audio"]["devices"].get("Target", [])
            device_names = [
                dev.get("name") or dev.get("description", "")
                for dev in raw_devices
                if dev.get("name") or dev.get("description")
            ]
            return target_names, device_names
        except Exception:
            return [], []

    def get_config_rows(self):
        settings = self._settings()
        current_master = settings.get("master_name", "")
        current_speaker = settings.get("speaker_name", "")
        current_headphone = settings.get("headphone_name", "")

        target_names, device_names = self._fetch_device_options()

        # ── PipeWeaver target name ──────────────────────────────────────────
        if target_names:
            if current_master and current_master not in target_names:
                target_names.insert(0, current_master)
            elif not current_master:
                # Nothing saved yet — auto-save the first available option
                current_master = target_names[0]
                self._save_setting("master_name", current_master)
            master_row = Adw.ComboRow(title="PipeWeaver target name")
            master_row.set_tooltip_text("The managed PipeWeaver target (master channel)")
            master_row.set_model(self._make_string_list(target_names))
            master_row.set_selected(self._combo_index(target_names, current_master))
            master_row.connect("notify::selected", self._on_master_combo_changed, target_names)
        else:
            master_row = Adw.EntryRow(title="PipeWeaver target name")
            master_row.set_tooltip_text("Name of the managed PipeWeaver target, e.g. Master Channel")
            master_row.set_text(current_master)
            master_row.connect("notify::text", self.on_master_changed)

        # ── Speaker device ──────────────────────────────────────────────────
        if device_names:
            if current_speaker and current_speaker not in device_names:
                device_names_speaker = [current_speaker] + device_names
            else:
                device_names_speaker = list(device_names)
            if not current_speaker:
                current_speaker = device_names_speaker[0]
                self._save_setting("speaker_name", current_speaker)
            speaker_row = Adw.ComboRow(title="Speaker device")
            speaker_row.set_tooltip_text("Node name of the speaker output")
            speaker_row.set_model(self._make_string_list(device_names_speaker))
            speaker_row.set_selected(self._combo_index(device_names_speaker, current_speaker))
            speaker_row.connect("notify::selected", self._on_speaker_combo_changed, device_names_speaker)
        else:
            speaker_row = Adw.EntryRow(title="Speaker device match")
            speaker_row.set_tooltip_text("Node name or substring of the device description")
            speaker_row.set_text(current_speaker)
            speaker_row.connect("notify::text", self.on_speaker_name_changed)

        # ── Headphone device ────────────────────────────────────────────────
        if device_names:
            if current_headphone and current_headphone not in device_names:
                device_names_headphone = [current_headphone] + device_names
            else:
                device_names_headphone = list(device_names)
            if not current_headphone:
                current_headphone = device_names_headphone[0]
                self._save_setting("headphone_name", current_headphone)
            headphone_row = Adw.ComboRow(title="Headphone device")
            headphone_row.set_tooltip_text("Node name of the headphone/headset output")
            headphone_row.set_model(self._make_string_list(device_names_headphone))
            headphone_row.set_selected(self._combo_index(device_names_headphone, current_headphone))
            headphone_row.connect("notify::selected", self._on_headphone_combo_changed, device_names_headphone)
        else:
            headphone_row = Adw.EntryRow(title="Headphone device match")
            headphone_row.set_tooltip_text("Node name or substring of the device description")
            headphone_row.set_text(current_headphone)
            headphone_row.connect("notify::text", self.on_headphone_name_changed)

        return [master_row, speaker_row, headphone_row]

    # ── Combo callbacks ─────────────────────────────────────────────────────
    def _on_master_combo_changed(self, combo, _, items):
        idx = combo.get_selected()
        if 0 <= idx < len(items):
            self._save_setting("master_name", items[idx])
            self.refresh_state(force=True)

    def _on_speaker_combo_changed(self, combo, _, items):
        idx = combo.get_selected()
        if 0 <= idx < len(items):
            self._save_setting("speaker_name", items[idx])
            self.refresh_state(force=True)

    def _on_headphone_combo_changed(self, combo, _, items):
        idx = combo.get_selected()
        if 0 <= idx < len(items):
            self._save_setting("headphone_name", items[idx])
            self.refresh_state(force=True)

    # ── Entry fallback callbacks ────────────────────────────────────────────
    def on_master_changed(self, row, _):
        self._save_setting("master_name", row.get_text())
        self.refresh_state(force=True)

    def on_speaker_name_changed(self, row, _):
        self._save_setting("speaker_name", row.get_text())
        self.refresh_state(force=True)

    def on_headphone_name_changed(self, row, _):
        self._save_setting("headphone_name", row.get_text())
        self.refresh_state(force=True)

    def _save_setting(self, key, value):
        settings = self.get_settings() or {}
        settings[key] = value
        self.set_settings(settings)

    def _init_settings(self):
        """Write default values once at startup; never called on every tick."""
        settings = self.get_settings() or {}
        changed = False
        for key, default in [
            ("master_name", ""),
            ("speaker_name", ""),
            ("headphone_name", ""),
        ]:
            if key not in settings:
                settings[key] = default
                changed = True
        if changed:
            self.set_settings(settings)

    def _settings(self) -> dict:
        return self.get_settings() or {}

    def _http_get_json(self, urls):
        last_error = None
        for url in urls:
            try:
                with urllib.request.urlopen(url, timeout=3) as response:
                    return json.load(response)
            except Exception as e:
                last_error = e
        raise RuntimeError(f"PipeWeaver API unreachable: {last_error}")

    def _http_post_json(self, urls, payload):
        data = json.dumps(payload).encode("utf-8")
        last_error = None
        for url in urls:
            try:
                request = urllib.request.Request(
                    url,
                    data=data,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=5) as response:
                    return json.load(response)
            except Exception as e:
                last_error = e
        raise RuntimeError(f"PipeWeaver command failed: {last_error}")

    def _get_status_data(self):
        return self._http_get_json(self.API_STATUS_URLS)

    def _pipeweaver_command(self, command):
        result = self._http_post_json(self.API_COMMAND_URLS, {"Pipewire": command})
        if isinstance(result, dict):
            pipewire = result.get("Pipewire")
            if pipewire == "Ok":
                return
            if isinstance(pipewire, dict) and pipewire.get("Err"):
                raise RuntimeError(pipewire["Err"])
        raise RuntimeError(f"Unexpected PipeWeaver response: {result}")

    def _master_profile_device(self, data):
        master_name = self._settings().get("master_name", "").strip()
        try:
            devices = data["audio"]["profile"]["devices"]["targets"]["physical_devices"]
        except KeyError as exc:
            raise RuntimeError(
                f"Unexpected PipeWeaver API shape — missing key {exc}. "
                "Check that PipeWeaver is running and the API schema matches."
            ) from exc
        for dev in devices:
            description = dev.get("description", {})
            if description.get("name") == master_name or description.get("id") == master_name:
                return dev
        for dev in devices:
            description = dev.get("description", {})
            if master_name and master_name.lower() in (description.get("name", "").lower()):
                return dev
        raise RuntimeError(f"Master target not found: {master_name}")

    def _match_text(self, candidate: Optional[str], needle: str) -> bool:
        if not candidate or not needle:
            return False
        candidate = candidate.strip().lower()
        needle = needle.strip().lower()
        return candidate == needle or needle in candidate

    def _find_physical_target(self, data, match_value: str):
        try:
            targets = data["audio"]["devices"]["Target"]
        except KeyError as exc:
            raise RuntimeError(
                f"Unexpected PipeWeaver API shape — missing key {exc}. "
                "Check that PipeWeaver is running and the API schema matches."
            ) from exc
        if not match_value:
            return None

        for dev in targets:
            if self._match_text(dev.get("name"), match_value):
                return dev
        for dev in targets:
            if self._match_text(dev.get("description"), match_value):
                return dev
        return None

    def _resolve_toggle_targets(self, data) -> Tuple[dict, dict]:
        settings = self._settings()
        speaker = self._find_physical_target(data, settings["speaker_name"])
        headphone = self._find_physical_target(data, settings["headphone_name"])

        if speaker is None:
            raise RuntimeError(f"Speaker target not found: {settings['speaker_name']}")
        if headphone is None:
            raise RuntimeError(f"Headphone target not found: {settings['headphone_name']}")
        return speaker, headphone

    def _get_current_target(self, data, master) -> Optional[str]:
        """Return the name of the currently active target using pre-fetched API data."""
        attached = master.get("attached_devices") or []
        if attached:
            return attached[0].get("name") or attached[0].get("description")

        default_target = data["audio"].get("defaults", {}).get("Target")
        default_target_id = default_target.get("Unmanaged") if isinstance(default_target, dict) else None
        if default_target_id is None:
            return None

        for dev in data["audio"].get("devices", {}).get("Target", []):
            if dev.get("node_id") == default_target_id:
                return dev.get("name") or dev.get("description")
        return None

    def _show_error(self, error):
        self.last_error = str(error)
        self.set_media(media_path=os.path.join(self.plugin_base.PATH, "assets", "icons", "unknown.svg"), size=0.75)
        self.set_top_label("")
        self.set_center_label("")
        self.set_bottom_label("")

    def _is_configured(self) -> bool:
        s = self._settings()
        return bool(s.get("master_name") and s.get("speaker_name") and s.get("headphone_name"))

    def _show_not_configured(self):
        self.set_media(media_path=os.path.join(self.plugin_base.PATH, "assets", "icons", "unknown.svg"), size=0.75)
        self.set_top_label("")
        self.set_center_label("")
        self.set_bottom_label("")

    def refresh_state(self, force: bool = False):
        if not self._is_configured():
            self._show_not_configured()
            return
        try:
            data = self._get_status_data()
            master = self._master_profile_device(data)
            current = self._get_current_target(data, master)
            speaker, headphone = self._resolve_toggle_targets(data)
        except Exception as e:
            self._show_error(e)
            return

        if not force and current == self.current_target_name:
            return

        self.current_target_name = current
        settings = self._settings()
        speaker_name = speaker.get("name") or speaker.get("description") or "speaker"
        headphone_name = headphone.get("name") or headphone.get("description") or "headphones"

        if self._match_text(current, settings.get("headphone_name", "")):
            icon = os.path.join(self.plugin_base.PATH, "assets", "icons", "headphones.svg")
        elif self._match_text(current, settings.get("speaker_name", "")):
            icon = os.path.join(self.plugin_base.PATH, "assets", "icons", "speaker.svg")
        else:
            icon = os.path.join(self.plugin_base.PATH, "assets", "icons", "unknown.svg")

        if force or icon != self.current_icon:
            self.set_media(media_path=icon, size=0.75)
            self.current_icon = icon

        self.set_top_label("")
        self.set_center_label("")
        self.set_bottom_label("")

    def toggle_target(self):
        if not self._is_configured():
            raise RuntimeError("Plugin not configured — set master, speaker and headphone names first.")
        data = self._get_status_data()
        master = self._master_profile_device(data)
        speaker, headphone = self._resolve_toggle_targets(data)
        master_id = master.get("description", {}).get("id")
        if not master_id:
            raise RuntimeError("Master target has no ID")

        current = self._get_current_target(data, master)
        next_target = speaker if current == (headphone.get("name") or headphone.get("description")) else headphone
        next_target_id = next_target.get("node_id")
        if next_target_id is None:
            raise RuntimeError("Target has no node_id")

        attached = master.get("attached_devices") or []
        for idx in range(len(attached) - 1, -1, -1):
            self._pipeweaver_command({"RemovePhysicalNode": [master_id, idx]})

        self._pipeweaver_command({"AttachPhysicalNode": [master_id, next_target_id]})
