import json
import os
import urllib.request
from typing import Optional, Tuple

import gi
from src.backend.PluginManager.ActionBase import ActionBase
from src.backend.DeckManagement.InputIdentifier import Input

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw


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

    def get_config_rows(self):
        master_row = Adw.EntryRow(title="PipeWeaver target name")
        master_row.set_subtitle("Name des verwalteten PipeWeaver-Targets, z. B. Master Channel")

        speaker_row = Adw.EntryRow(title="Speaker device match")
        speaker_row.set_subtitle("Node-Name oder Teilstring der Beschreibung")

        headphone_row = Adw.EntryRow(title="Headphone device match")
        headphone_row.set_subtitle("Node-Name oder Teilstring der Beschreibung")

        poll_row = Adw.SpinRow.new_with_range(0.2, 5.0, 0.1)
        poll_row.set_title("Poll interval hint (unused by app tick)")
        poll_row.set_subtitle("Nur zur Dokumentation; StreamController ruft on_tick selbst auf")

        settings = self._settings()
        master_row.set_text(settings["master_name"])
        speaker_row.set_text(settings["speaker_name"])
        headphone_row.set_text(settings["headphone_name"])
        poll_row.set_value(settings.get("poll_interval", 1.0))

        master_row.connect("notify::text", self.on_master_changed)
        speaker_row.connect("notify::text", self.on_speaker_name_changed)
        headphone_row.connect("notify::text", self.on_headphone_name_changed)
        poll_row.connect("changed", self.on_poll_changed)

        return [master_row, speaker_row, headphone_row, poll_row]

    def on_master_changed(self, row, _):
        self._save_setting("master_name", row.get_text())
        self.refresh_state(force=True)

    def on_speaker_name_changed(self, row, _):
        self._save_setting("speaker_name", row.get_text())
        self.refresh_state(force=True)

    def on_headphone_name_changed(self, row, _):
        self._save_setting("headphone_name", row.get_text())
        self.refresh_state(force=True)

    def on_poll_changed(self, row):
        self._save_setting("poll_interval", round(row.get_value(), 1))

    def _save_setting(self, key, value):
        settings = self.get_settings()
        settings[key] = value
        self.set_settings(settings)

    def _settings(self):
        settings = self.get_settings()
        settings.setdefault("master_name", "Master Channel")
        settings.setdefault("speaker_name", "alsa_output.usb-bestechnic_EDIFIER_M60_20160406.1-00.analog-stereo")
        settings.setdefault("headphone_name", "xlrdock-sink")
        settings.setdefault("poll_interval", 1.0)
        self.set_settings(settings)
        return settings

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
        master_name = self._settings()["master_name"].strip()
        devices = data["audio"]["profile"]["devices"]["targets"]["physical_devices"]
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
        targets = data["audio"]["devices"]["Target"]
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

    def get_current_target(self) -> Optional[str]:
        data = self._get_status_data()
        master = self._master_profile_device(data)
        attached = master.get("attached_devices") or []
        if attached:
            return attached[0].get("name") or attached[0].get("description")

        default_target = data["audio"].get("defaults", {}).get("Target")
        default_target_id = default_target.get("Unmanaged") if isinstance(default_target, dict) else None
        if default_target_id is None:
            return None

        for dev in data["audio"]["devices"]["Target"]:
            if dev.get("node_id") == default_target_id:
                return dev.get("name") or dev.get("description")
        return None

    def _show_error(self, error):
        message = str(error)
        self.last_error = message
        self.set_media(media_path=os.path.join(self.plugin_base.PATH, "assets", "icons", "unknown.svg"), size=0.82)
        self.set_top_label("Audio")
        self.set_center_label("ERR")
        self.set_bottom_label(message[:18])

    def refresh_state(self, force: bool = False):
        try:
            data = self._get_status_data()
            current = self.get_current_target()
            speaker, headphone = self._resolve_toggle_targets(data)
        except Exception as e:
            self._show_error(e)
            return

        if not force and current == self.current_target_name:
            return

        self.current_target_name = current
        speaker_name = speaker.get("name") or speaker.get("description") or "speaker"
        headphone_name = headphone.get("name") or headphone.get("description") or "headphones"

        if current == headphone.get("name") or current == headphone.get("description"):
            icon = os.path.join(self.plugin_base.PATH, "assets", "icons", "headphones.svg")
            top = "Audio"
            center = ""
            bottom = "Headphones"
        elif current == speaker.get("name") or current == speaker.get("description"):
            icon = os.path.join(self.plugin_base.PATH, "assets", "icons", "speaker.svg")
            top = "Audio"
            center = ""
            bottom = "Speaker"
        else:
            icon = os.path.join(self.plugin_base.PATH, "assets", "icons", "unknown.svg")
            top = "Audio"
            center = "?"
            bottom = (current or f"{speaker_name}/{headphone_name}")[:18]

        if force or icon != self.current_icon:
            self.set_media(media_path=icon, size=0.82)
            self.current_icon = icon

        self.set_top_label(top)
        self.set_center_label(center)
        self.set_bottom_label(bottom)

    def toggle_target(self):
        data = self._get_status_data()
        master = self._master_profile_device(data)
        speaker, headphone = self._resolve_toggle_targets(data)
        master_id = master.get("description", {}).get("id")
        if not master_id:
            raise RuntimeError("Master target has no ID")

        current = self.get_current_target()
        next_target = speaker if current == (headphone.get("name") or headphone.get("description")) else headphone
        next_target_id = next_target.get("node_id")
        if next_target_id is None:
            raise RuntimeError("Target has no node_id")

        attached = master.get("attached_devices") or []
        for idx in range(len(attached) - 1, -1, -1):
            self._pipeweaver_command({"RemovePhysicalNode": [master_id, idx]})

        self._pipeweaver_command({"AttachPhysicalNode": [master_id, next_target_id]})
