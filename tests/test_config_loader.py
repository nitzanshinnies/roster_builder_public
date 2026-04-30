import unittest

from roster_builder_app.config_loader import DEFAULT_HISTORY_FILE, DEFAULT_OUTPUT_DIR, merge_args


def _cli_args(**overrides) -> dict:
    values = {
        "algorithm": "srr",
        "commit": False,
        "constraints": None,
        "guards": None,
        "history_file": None,
        "output_dir": None,
        "patrol": None,
        "roster_length": None,
        "rotation_start": None,
        "shift_duration": None,
        "start_date": "2026-05-04 06:00",
    }
    values.update(overrides)
    return values


class MergeArgsTests(unittest.TestCase):
    def test_cli_paths_override_config_paths(self) -> None:
        merged = merge_args(
            _cli_args(
                history_file="cli_history.json",
                output_dir="cli_output",
            ),
            {
                "guards": ["A"],
                "history_file": "config_history.json",
                "output_dir": "config_output",
            },
        )

        self.assertEqual(merged["history_file"], "cli_history.json")
        self.assertEqual(merged["output_dir"], "cli_output")

    def test_config_paths_are_preserved_when_cli_does_not_override(self) -> None:
        merged = merge_args(
            _cli_args(),
            {
                "guards": ["A"],
                "history_file": "config_history.json",
                "output_dir": "config_output",
            },
        )

        self.assertEqual(merged["history_file"], "config_history.json")
        self.assertEqual(merged["output_dir"], "config_output")

    def test_defaults_are_used_without_config_paths(self) -> None:
        merged = merge_args(_cli_args(), {"guards": ["A"]})

        self.assertEqual(merged["history_file"], DEFAULT_HISTORY_FILE)
        self.assertEqual(merged["output_dir"], DEFAULT_OUTPUT_DIR)


if __name__ == "__main__":
    unittest.main()
