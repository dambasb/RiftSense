import unittest

from riftsense.updater import (
    CHECKSUM_ASSET_NAME,
    EXE_ASSET_NAME,
    UpdateError,
    compare_versions,
    is_newer_version,
    parse_sha256_text,
    select_update_from_releases,
)


class UpdaterTests(unittest.TestCase):
    def test_semver_comparison_handles_beta_builds(self):
        self.assertTrue(is_newer_version("1.0.0-beta.2", "1.0.0-beta.1"))
        self.assertTrue(is_newer_version("1.0.0", "1.0.0-beta.9"))
        self.assertEqual(compare_versions("v1.2.3", "1.2.3"), 0)
        self.assertFalse(is_newer_version("1.0.0-beta.1", "1.0.0"))

    def test_release_selection_requires_both_verified_assets(self):
        releases = [
            {
                "tag_name": "v1.0.0-beta.3",
                "draft": False,
                "name": "RiftSense beta 3",
                "body": "Newest",
                "html_url": "https://github.com/dambasb/RiftSense/releases/tag/v1.0.0-beta.3",
                "assets": [
                    {
                        "name": EXE_ASSET_NAME,
                        "browser_download_url": (
                            "https://github.com/dambasb/RiftSense/releases/download/"
                            "v1.0.0-beta.3/RiftSense.exe"
                        ),
                    },
                    {
                        "name": CHECKSUM_ASSET_NAME,
                        "browser_download_url": (
                            "https://github.com/dambasb/RiftSense/releases/download/"
                            "v1.0.0-beta.3/RiftSense.exe.sha256"
                        ),
                    },
                ],
            },
            {
                "tag_name": "v9.0.0",
                "draft": True,
                "assets": [],
            },
        ]
        update = select_update_from_releases(releases, "1.0.0-beta.1")
        self.assertIsNotNone(update)
        self.assertEqual(update.version, "1.0.0-beta.3")

    def test_release_selection_rejects_untrusted_asset_url(self):
        releases = [
            {
                "tag_name": "v1.0.1",
                "draft": False,
                "assets": [
                    {
                        "name": EXE_ASSET_NAME,
                        "browser_download_url": "https://example.com/RiftSense.exe",
                    },
                    {
                        "name": CHECKSUM_ASSET_NAME,
                        "browser_download_url": (
                            "https://github.com/dambasb/RiftSense/releases/download/"
                            "v1.0.1/RiftSense.exe.sha256"
                        ),
                    },
                ],
            }
        ]
        with self.assertRaises(UpdateError):
            select_update_from_releases(releases, "1.0.0")

    def test_checksum_parser_accepts_standard_sha256_file(self):
        digest = "a" * 64
        self.assertEqual(
            parse_sha256_text(f"{digest}  RiftSense.exe\n"),
            digest,
        )


if __name__ == "__main__":
    unittest.main()
