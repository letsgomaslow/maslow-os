import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from maslow_voice.config import Settings, validate_settings, validate_endpoint
from maslow_voice.coordinator import clean_environment, hermes_configuration
from maslow_voice.errors import VoiceError
from maslow_voice.models import verify_speech
from maslow_voice.voices import LIVEKIT_VOICES, OPENAI_VOICES


class ConfigurationTests(unittest.TestCase):
    def test_credentials_cannot_enter_preferences(self):
        with self.assertRaises(VoiceError):
            validate_settings({"api_key": "sensitive"})
        for url in ("https://user:secret@example.test", "file:///tmp/model", "http://host/#secret", "http://host/?key=secret"):
            with self.assertRaises(VoiceError):
                validate_endpoint(url)
        self.assertEqual(validate_endpoint("https://model.example.test/v1/"), "https://model.example.test/v1")

    def test_atomic_saved_preferences_and_permissions(self):
        with tempfile.TemporaryDirectory() as root:
            settings = Settings(root)
            settings.update({"mode": "offline", "model": "chosen-local-model"})
            self.assertEqual(Settings(root).value["mode"], "offline")
            self.assertEqual(settings.path.stat().st_mode & 0o777, 0o600)
            settings.update({"realtime_voice": "marin", "livekit_voice": "Olivia"})
            self.assertEqual(Settings(root).value["realtime_voice"], "marin")
            self.assertEqual(Settings(root).value["livekit_voice"], "Olivia")

    def test_cloud_voice_defaults_and_validation_follow_the_curated_lists(self):
        self.assertEqual(validate_settings({})["realtime_voice"], "cedar")
        self.assertEqual(validate_settings({})["livekit_voice"], "Ashley")
        self.assertEqual(validate_settings({"realtime_voice": OPENAI_VOICES[-1]})["realtime_voice"], OPENAI_VOICES[-1])
        self.assertEqual(validate_settings({"livekit_voice": LIVEKIT_VOICES[-1]})["livekit_voice"], LIVEKIT_VOICES[-1])
        with self.assertRaises(VoiceError):
            validate_settings({"realtime_voice": "unsupported"})
        with self.assertRaises(VoiceError):
            validate_settings({"livekit_voice": "unsupported"})
        for value in ([], {}):
            with self.assertRaises(VoiceError):
                validate_settings({"realtime_voice": value})
            with self.assertRaises(VoiceError):
                validate_settings({"livekit_voice": value})

    def test_dedicated_hermes_profile_has_no_fallback_or_broad_tools(self):
        config = hermes_configuration({"provider": "custom", "default": "local"}, "token", 9000, "/work")
        self.assertEqual(config["platform_toolsets"]["api_server"], ["terminal", "file", "maslow_voice"])
        self.assertEqual(config["plugins"]["enabled"], ["maslow-voice"])
        self.assertTrue(config["plugins"]["entries"]["maslow-voice"]["enabled"])
        self.assertIsNone(config["fallback_model"])
        self.assertFalse(config["compression"]["enabled"])
        self.assertFalse(config["security"]["allow_lazy_installs"])
        self.assertNotIn("api_key", config["model"])
        environment = clean_environment()
        self.assertEqual(environment["HERMES_DISABLE_LAZY_INSTALLS"], "1")
        self.assertNotIn("HERMES_NO_AUTO_INSTALL", environment)

    def test_speech_readiness_checks_bytes_and_refuses_symlinks(self):
        with tempfile.TemporaryDirectory() as root:
            target = Path(root) / "model"
            target.write_bytes(b"good model")
            pack = {"files": [{"path": "model", "size": 10, "sha256": hashlib.sha256(b"good model").hexdigest()}]}
            self.assertTrue(verify_speech(root, pack))
            target.write_bytes(b"bad  model")
            self.assertFalse(verify_speech(root, pack))
            other = Path(root) / "outside"
            other.write_bytes(b"good model")
            target.unlink()
            target.symlink_to(other)
            self.assertFalse(verify_speech(root, pack))
