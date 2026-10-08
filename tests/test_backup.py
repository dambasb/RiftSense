import json
import stat
import tempfile
import threading
import time
import unittest
import warnings
import zipfile
from pathlib import Path
from unittest.mock import patch

from riftsense.core import backup
from riftsense.core.backup import (
    BACKUP_FORMAT_VERSION,
    BackupLayout,
    BackupValidationError,
    RestoreTransactionError,
    create_backup,
    restore_backup_transactional,
    validate_backup,
)
from riftsense.core.storage import persistence_maintenance, write_json_atomic


def make_layout(root: Path) -> BackupLayout:
    return BackupLayout(
        settings=root / "settings.json",
        history=root / "history",
        player_memory=root / "player_memory.json",
        performance_history=root / "performance_history.json",
        rank_progress=root / "rank_progress.json",
        ai_reviews=root / "ai_reviews",
    )


def seed_complete(layout: BackupLayout, marker: str) -> None:
    layout.settings.parent.mkdir(parents=True, exist_ok=True)
    layout.settings.write_text(json.dumps({"marker": marker}), encoding="utf-8")
    layout.history.mkdir(parents=True, exist_ok=True)
    (layout.history / "riot_account.json").write_text(
        json.dumps({"puuid": marker}),
        encoding="utf-8",
    )
    (layout.history / "games.csv").write_text(
        f"id,result\n{marker},WIN\n",
        encoding="utf-8",
    )
    layout.player_memory.write_text(
        json.dumps({"players": [marker]}),
        encoding="utf-8",
    )
    layout.performance_history.write_text(
        json.dumps([{"marker": marker}]),
        encoding="utf-8",
    )
    layout.rank_progress.write_text(
        json.dumps({"rank": marker}),
        encoding="utf-8",
    )
    layout.ai_reviews.mkdir(parents=True, exist_ok=True)
    (layout.ai_reviews / "review.json").write_text(
        json.dumps({"review": marker}),
        encoding="utf-8",
    )


def layout_state(layout: BackupLayout):
    state = {}
    for name, path in layout.components().items():
        if not path.exists():
            state[name] = ("missing",)
        elif path.is_file():
            state[name] = ("file", path.read_bytes())
        else:
            entries = []
            for child in sorted(path.rglob("*"), key=lambda item: item.as_posix()):
                relative = child.relative_to(path).as_posix()
                entries.append(
                    ("directory", relative)
                    if child.is_dir()
                    else ("file", relative, child.read_bytes())
                )
            state[name] = ("directory", tuple(entries))
    return state


def rewrite_zip(source: Path, destination: Path, mutate):
    with zipfile.ZipFile(source, "r") as original:
        entries = [(info.filename, original.read(info)) for info in original.infolist()]
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as rewritten:
        for name, payload in entries:
            rewritten.writestr(name, mutate(name, payload))


class BackupTests(unittest.TestCase):
    def test_new_backup_has_strict_manifest_sizes_and_checksums(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            layout = make_layout(root / "live")
            seed_complete(layout, "source")
            destination = root / "backup.zip"

            create_backup(layout, destination, application_version="test")

            with zipfile.ZipFile(destination) as archive:
                manifest = json.loads(archive.read("backup_manifest.json"))
                self.assertEqual(manifest["format_version"], BACKUP_FORMAT_VERSION)
                self.assertEqual(manifest["application_version"], "test")
                self.assertTrue(manifest["components"]["settings.json"])
                for entry in manifest["files"]:
                    payload = archive.read(entry["path"])
                    self.assertEqual(entry["size"], len(payload))
                    self.assertEqual(entry["sha256"], backup._sha256(payload))

    def test_changed_member_fails_checksum_before_live_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_layout = make_layout(root / "source")
            live_layout = make_layout(root / "live")
            seed_complete(source_layout, "source")
            seed_complete(live_layout, "live")
            valid = create_backup(
                source_layout,
                root / "valid.zip",
                application_version="test",
            )
            damaged = root / "damaged.zip"
            rewrite_zip(
                valid,
                damaged,
                lambda name, payload: (
                    b'{"marker":"tampered"}'
                    if name == "settings.json"
                    else payload
                ),
            )
            before = layout_state(live_layout)

            with self.assertRaisesRegex(BackupValidationError, "size check|checksum"):
                restore_backup_transactional(
                    damaged,
                    live_layout,
                    application_version="test",
                )

            self.assertEqual(layout_state(live_layout), before)

    def test_path_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path = root / "unsafe.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("settings.json", "{}")
                archive.writestr("../escape.json", "{}")
            with self.assertRaisesRegex(BackupValidationError, "unsafe path"):
                validate_backup(archive_path, root / "stage")
            self.assertFalse((root / "escape.json").exists())

    def test_windows_drive_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path = root / "unsafe-drive.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("settings.json", "{}")
                archive.writestr("C:\\outside.json", "{}")
            with self.assertRaisesRegex(BackupValidationError, "drive path"):
                validate_backup(archive_path, root / "stage")

    def test_duplicate_and_symlink_members_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            duplicate = root / "duplicate.zip"
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                with zipfile.ZipFile(duplicate, "w") as archive:
                    archive.writestr("settings.json", "{}")
                    archive.writestr("SETTINGS.JSON", "{}")
            with self.assertRaisesRegex(BackupValidationError, "duplicate paths"):
                validate_backup(duplicate, root / "duplicate-stage")

            symlink = root / "symlink.zip"
            info = zipfile.ZipInfo("history/link.json")
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            with zipfile.ZipFile(symlink, "w") as archive:
                archive.writestr("settings.json", "{}")
                archive.writestr(info, "settings.json")
            with self.assertRaisesRegex(BackupValidationError, "symbolic-link"):
                validate_backup(symlink, root / "symlink-stage")

    def test_unreasonable_member_size_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path = root / "large.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("settings.json", '{"padding":"1234567890"}')
            with patch.object(backup, "MAX_MEMBER_SIZE", 10):
                with self.assertRaisesRegex(BackupValidationError, "unreasonably large"):
                    validate_backup(archive_path, root / "stage")

    def test_invalid_json_is_rejected_before_live_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path = root / "invalid-json.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("settings.json", "{broken")
            layout = make_layout(root / "live")
            seed_complete(layout, "live")
            before = layout_state(layout)

            with self.assertRaisesRegex(BackupValidationError, "JSON is invalid"):
                restore_backup_transactional(
                    archive_path,
                    layout,
                    application_version="test",
                )

            self.assertEqual(layout_state(layout), before)

    def test_successful_restore_replaces_complete_modern_backup_unit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_layout = make_layout(root / "source")
            source_layout.settings.parent.mkdir(parents=True)
            source_layout.settings.write_text('{"marker":"source"}', encoding="utf-8")
            source_layout.history.mkdir()
            (source_layout.history / "new.json").write_text(
                '{"value":1}', encoding="utf-8"
            )
            source_layout.player_memory.write_text('{"new":true}', encoding="utf-8")
            source_layout.ai_reviews.mkdir()
            archive_path = create_backup(
                source_layout,
                root / "backup.zip",
                application_version="test",
            )

            live_layout = make_layout(root / "live")
            seed_complete(live_layout, "old")
            safety_path = root / "recovery" / "before.zip"
            result = restore_backup_transactional(
                archive_path,
                live_layout,
                application_version="test",
                safety_backup=safety_path,
            )

            self.assertFalse(result.legacy)
            self.assertEqual(result.safety_backup, safety_path)
            self.assertTrue(safety_path.is_file())
            validate_backup(safety_path, root / "safety-stage")
            self.assertEqual(json.loads(live_layout.settings.read_text()), {"marker": "source"})
            self.assertTrue((live_layout.history / "new.json").exists())
            self.assertFalse((live_layout.history / "games.csv").exists())
            self.assertFalse(live_layout.performance_history.exists())
            self.assertFalse(live_layout.rank_progress.exists())
            self.assertTrue(live_layout.ai_reviews.is_dir())

    def test_failures_after_live_changes_roll_back_exact_state(self):
        stages = (
            "after_first_restored_file",
            "halfway",
            "before_verification",
            "during_verification",
        )
        for stage in stages:
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                source_layout = make_layout(root / "source")
                live_layout = make_layout(root / "live")
                seed_complete(source_layout, "source")
                seed_complete(live_layout, "live")
                live_layout.player_memory.unlink()
                (live_layout.history / "only-before.txt").write_text(
                    "preserve me", encoding="utf-8"
                )
                archive_path = create_backup(
                    source_layout,
                    root / "backup.zip",
                    application_version="test",
                )
                before = layout_state(live_layout)

                def fail(current_stage, _path):
                    if current_stage == stage:
                        raise OSError(f"injected {stage}")

                with self.assertRaises(RestoreTransactionError) as raised:
                    restore_backup_transactional(
                        archive_path,
                        live_layout,
                        application_version="test",
                        failure_injector=fail,
                    )

                self.assertTrue(raised.exception.rollback_performed)
                self.assertEqual(layout_state(live_layout), before)

    def test_atomic_replacement_failure_rolls_back_created_and_deleted_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_layout = make_layout(root / "source")
            live_layout = make_layout(root / "live")
            seed_complete(source_layout, "source")
            seed_complete(live_layout, "live")
            live_layout.player_memory.unlink()
            source_layout.rank_progress.unlink()
            archive_path = create_backup(
                source_layout,
                root / "backup.zip",
                application_version="test",
            )
            before = layout_state(live_layout)
            real_write = backup.write_json_bytes_atomic
            calls = 0

            def fail_once(path, payload, *, validate=True):
                nonlocal calls
                calls += 1
                if calls == 2:
                    return False, "injected atomic replacement failure"
                return real_write(path, payload, validate=validate)

            with patch.object(backup, "write_json_bytes_atomic", side_effect=fail_once):
                with self.assertRaises(RestoreTransactionError) as raised:
                    restore_backup_transactional(
                        archive_path,
                        live_layout,
                        application_version="test",
                    )

            self.assertTrue(raised.exception.rollback_performed)
            self.assertEqual(layout_state(live_layout), before)
            self.assertFalse(live_layout.player_memory.exists())
            self.assertTrue(live_layout.rank_progress.exists())

    def test_rollback_failure_preserves_manual_recovery_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_layout = make_layout(root / "source")
            live_layout = make_layout(root / "live")
            seed_complete(source_layout, "source")
            seed_complete(live_layout, "live")
            archive_path = create_backup(
                source_layout,
                root / "backup.zip",
                application_version="test",
            )

            def fail_after_first(stage, _path):
                if stage == "after_first_restored_file":
                    raise OSError("injected restore failure")

            with patch.object(backup, "_rollback", side_effect=OSError("rollback failed")):
                with self.assertRaises(RestoreTransactionError) as raised:
                    restore_backup_transactional(
                        archive_path,
                        live_layout,
                        application_version="test",
                        failure_injector=fail_after_first,
                        recovery_parent=root / "recoveries",
                    )

            self.assertFalse(raised.exception.rollback_performed)
            recovery_path = raised.exception.recovery_path
            self.assertIsNotNone(recovery_path)
            self.assertTrue(recovery_path.is_dir())
            self.assertTrue((recovery_path / "rollback").is_dir())
            self.assertTrue((recovery_path / "staging").is_dir())

    def test_failure_before_live_modification_needs_no_rollback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_layout = make_layout(root / "source")
            live_layout = make_layout(root / "live")
            seed_complete(source_layout, "source")
            seed_complete(live_layout, "live")
            archive_path = create_backup(
                source_layout,
                root / "backup.zip",
                application_version="test",
            )
            before = layout_state(live_layout)

            def fail(stage, _path):
                if stage == "before_live_modification":
                    raise OSError("injected pre-apply failure")

            with self.assertRaisesRegex(OSError, "pre-apply"):
                restore_backup_transactional(
                    archive_path,
                    live_layout,
                    application_version="test",
                    failure_injector=fail,
                )
            self.assertEqual(layout_state(live_layout), before)

    def test_valid_legacy_backup_restores_only_components_it_contains(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path = root / "legacy.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr(
                    "backup_manifest.json",
                    json.dumps({"app": "RiftSense", "format": 3}),
                )
                archive.writestr("settings.json", '{"legacy":true}')
                archive.writestr("history/legacy.json", '{"match":1}')

            live_layout = make_layout(root / "live")
            seed_complete(live_layout, "live")
            old_memory = live_layout.player_memory.read_bytes()
            result = restore_backup_transactional(
                archive_path,
                live_layout,
                application_version="test",
            )

            self.assertTrue(result.legacy)
            self.assertEqual(json.loads(live_layout.settings.read_text()), {"legacy": True})
            self.assertTrue((live_layout.history / "legacy.json").exists())
            self.assertEqual(live_layout.player_memory.read_bytes(), old_memory)

    def test_valid_manifestless_legacy_backup_remains_supported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path = root / "manifestless.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("settings.json", '{"legacy":"manifestless"}')
            live_layout = make_layout(root / "live")
            seed_complete(live_layout, "live")

            result = restore_backup_transactional(
                archive_path,
                live_layout,
                application_version="test",
            )

            self.assertTrue(result.legacy)
            self.assertEqual(
                json.loads(live_layout.settings.read_text()),
                {"legacy": "manifestless"},
            )
            self.assertTrue((live_layout.history / "games.csv").exists())

    def test_maintenance_gate_blocks_conflicting_persistence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            started = threading.Event()
            finished = threading.Event()

            def writer():
                started.set()
                write_json_atomic(path, {"done": True})
                finished.set()

            with persistence_maintenance():
                thread = threading.Thread(target=writer)
                thread.start()
                self.assertTrue(started.wait(1.0))
                time.sleep(0.03)
                self.assertFalse(finished.is_set())
            thread.join(1.0)
            self.assertTrue(finished.is_set())
            self.assertEqual(json.loads(path.read_text()), {"done": True})


if __name__ == "__main__":
    unittest.main()
