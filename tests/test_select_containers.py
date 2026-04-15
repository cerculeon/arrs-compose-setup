"""
Tests for select_containers.py

Run with:
    pytest tests/test_select_containers.py -v
"""

import sys
from pathlib import Path
from unittest.mock import patch, call

import pytest
import yaml

# Ensure the project root is on the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from select_containers import (
    parse_services,
    interactive_select,
    build_compose_command,
    run_command,
    main,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

SAMPLE_SERVICES = {
    "sabnzbd": {"image": "linuxserver/sabnzbd"},
    "sonarr": {"image": "linuxserver/sonarr"},
    "radarr": {"image": "linuxserver/radarr"},
    "plex": {"image": "linuxserver/plex"},
}

SAMPLE_COMPOSE = {"services": SAMPLE_SERVICES}


@pytest.fixture
def compose_file(tmp_path):
    """Write a minimal compose file and return its path string."""
    f = tmp_path / "test-compose.yml"
    f.write_text(yaml.dump(SAMPLE_COMPOSE))
    return str(f)


@pytest.fixture
def empty_compose_file(tmp_path):
    """Compose file with no services key."""
    f = tmp_path / "empty-compose.yml"
    f.write_text(yaml.dump({"version": "3"}))
    return str(f)


@pytest.fixture
def services():
    return list(SAMPLE_SERVICES.keys())


# ---------------------------------------------------------------------------
# parse_services
# ---------------------------------------------------------------------------


class TestParseServices:
    def test_returns_all_service_names(self, compose_file):
        result = parse_services(compose_file)
        assert set(result) == set(SAMPLE_SERVICES.keys())

    def test_returns_list_type(self, compose_file):
        result = parse_services(compose_file)
        assert isinstance(result, list)

    def test_correct_service_count(self, compose_file):
        result = parse_services(compose_file)
        assert len(result) == len(SAMPLE_SERVICES)

    def test_empty_services_section_returns_empty_list(self, empty_compose_file):
        result = parse_services(empty_compose_file)
        assert result == []

    def test_missing_file_raises_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            parse_services("/nonexistent/path/compose.yml")

    def test_single_service(self, tmp_path):
        f = tmp_path / "single.yml"
        f.write_text(yaml.dump({"services": {"plex": {"image": "linuxserver/plex"}}}))
        result = parse_services(str(f))
        assert result == ["plex"]

    def test_preserves_service_names_exactly(self, compose_file):
        result = parse_services(compose_file)
        for name in SAMPLE_SERVICES:
            assert name in result


# ---------------------------------------------------------------------------
# build_compose_command
# ---------------------------------------------------------------------------


class TestBuildComposeCommand:
    def test_starts_with_docker_compose(self):
        cmd = build_compose_command("f.yml", "e.env", ["plex"])
        assert cmd[0] == "docker"
        assert cmd[1] == "compose"

    def test_includes_compose_file_flag(self):
        cmd = build_compose_command("myfile.yml", "e.env", ["plex"])
        assert "-f" in cmd
        idx = cmd.index("-f")
        assert cmd[idx + 1] == "myfile.yml"

    def test_includes_env_file_flag(self):
        cmd = build_compose_command("f.yml", "my.env", ["plex"])
        assert "--env-file" in cmd
        idx = cmd.index("--env-file")
        assert cmd[idx + 1] == "my.env"

    def test_includes_up_subcommand(self):
        cmd = build_compose_command("f.yml", "e.env", ["plex"])
        assert "up" in cmd

    def test_detach_flag_included_by_default(self):
        cmd = build_compose_command("f.yml", "e.env", ["plex"])
        assert "-d" in cmd

    def test_detach_flag_omitted_when_false(self):
        cmd = build_compose_command("f.yml", "e.env", ["plex"], detach=False)
        assert "-d" not in cmd

    def test_build_flag_omitted_by_default(self):
        cmd = build_compose_command("f.yml", "e.env", ["plex"])
        assert "--build" not in cmd

    def test_build_flag_included_when_true(self):
        cmd = build_compose_command("f.yml", "e.env", ["plex"], build=True)
        assert "--build" in cmd

    def test_single_service_appended(self):
        cmd = build_compose_command("f.yml", "e.env", ["plex"])
        assert "plex" in cmd

    def test_multiple_services_all_appended(self):
        cmd = build_compose_command("f.yml", "e.env", ["sonarr", "radarr", "plex"])
        assert "sonarr" in cmd
        assert "radarr" in cmd
        assert "plex" in cmd

    def test_services_appear_once_each(self):
        cmd = build_compose_command("f.yml", "e.env", ["sonarr", "radarr"])
        assert cmd.count("sonarr") == 1
        assert cmd.count("radarr") == 1

    def test_returns_list_type(self):
        cmd = build_compose_command("f.yml", "e.env", ["plex"])
        assert isinstance(cmd, list)

    def test_all_elements_are_strings(self):
        cmd = build_compose_command("f.yml", "e.env", ["plex"])
        assert all(isinstance(t, str) for t in cmd)


# ---------------------------------------------------------------------------
# interactive_select
# ---------------------------------------------------------------------------


class TestInteractiveSelect:
    def test_select_all_keyword_returns_all_services(self, services):
        with patch("builtins.input", return_value="all"):
            result = interactive_select(services)
        assert result == services

    def test_select_none_keyword_returns_empty(self, services):
        with patch("builtins.input", return_value="none"):
            result = interactive_select(services)
        assert result == []

    def test_empty_input_returns_empty(self, services):
        with patch("builtins.input", return_value=""):
            result = interactive_select(services)
        assert result == []

    def test_select_first_service_by_number(self, services):
        with patch("builtins.input", return_value="1"):
            result = interactive_select(services)
        assert result == [services[0]]

    def test_select_last_service_by_number(self, services):
        with patch("builtins.input", return_value=str(len(services))):
            result = interactive_select(services)
        assert result == [services[-1]]

    def test_select_multiple_by_number(self, services):
        with patch("builtins.input", return_value="1,3"):
            result = interactive_select(services)
        assert result == [services[0], services[2]]

    def test_select_with_spaces_around_commas(self, services):
        with patch("builtins.input", return_value="1, 2"):
            result = interactive_select(services)
        assert result == [services[0], services[1]]

    def test_duplicate_numbers_deduped(self, services):
        with patch("builtins.input", return_value="1,1,2"):
            result = interactive_select(services)
        assert result.count(services[0]) == 1

    def test_empty_services_list_returns_empty_without_prompting(self):
        result = interactive_select([])
        assert result == []

    def test_invalid_text_retries_then_succeeds(self, services):
        with patch("builtins.input", side_effect=["abc", "1"]):
            result = interactive_select(services)
        assert result == [services[0]]

    def test_out_of_range_number_retries_then_succeeds(self, services):
        high = str(len(services) + 1)
        with patch("builtins.input", side_effect=[high, "1"]):
            result = interactive_select(services)
        assert result == [services[0]]

    def test_zero_out_of_range_retries_then_succeeds(self, services):
        with patch("builtins.input", side_effect=["0", "2"]):
            result = interactive_select(services)
        assert result == [services[1]]

    def test_keyboard_interrupt_returns_empty(self, services):
        with patch("builtins.input", side_effect=KeyboardInterrupt):
            result = interactive_select(services)
        assert result == []

    def test_eof_error_returns_empty(self, services):
        with patch("builtins.input", side_effect=EOFError):
            result = interactive_select(services)
        assert result == []

    def test_selection_order_preserved(self, services):
        # Select items 3 then 1 — order should follow user input
        with patch("builtins.input", return_value="3,1"):
            result = interactive_select(services)
        assert result == [services[2], services[0]]


# ---------------------------------------------------------------------------
# run_command
# ---------------------------------------------------------------------------


class TestRunCommand:
    def test_returns_zero_on_success(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            assert run_command(["echo", "hello"]) == 0

    def test_returns_nonzero_on_failure(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1
            assert run_command(["false"]) == 1

    def test_passes_command_to_subprocess(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            run_command(["docker", "compose", "up", "-d"])
        mock_run.assert_called_once_with(["docker", "compose", "up", "-d"])


# ---------------------------------------------------------------------------
# main (integration-level)
# ---------------------------------------------------------------------------


class TestMain:
    def test_dry_run_returns_zero(self, compose_file, capsys):
        with patch("builtins.input", return_value="all"):
            rc = main(["--file", compose_file, "--env-file", "my.env"])
        assert rc == 0

    def test_dry_run_prints_dry_run_notice(self, compose_file, capsys):
        with patch("builtins.input", return_value="all"):
            main(["--file", compose_file, "--env-file", "my.env"])
        assert "Dry-run" in capsys.readouterr().out

    def test_dry_run_does_not_call_subprocess(self, compose_file):
        with patch("builtins.input", return_value="all"):
            with patch("select_containers.run_command") as mock_run:
                main(["--file", compose_file, "--env-file", "my.env"])
        mock_run.assert_not_called()

    def test_select_all_flag_includes_all_services(self, compose_file, capsys):
        main(["--file", compose_file, "--env-file", "my.env", "--all"])
        out = capsys.readouterr().out
        for svc in SAMPLE_SERVICES:
            assert svc in out

    def test_services_flag_includes_named_services(self, compose_file, capsys):
        main(["--file", compose_file, "--env-file", "my.env", "--services", "sonarr,plex"])
        out = capsys.readouterr().out
        assert "sonarr" in out
        assert "plex" in out

    def test_services_flag_excludes_unselected_services(self, compose_file, capsys):
        main(["--file", compose_file, "--env-file", "my.env", "--services", "sonarr"])
        out = capsys.readouterr().out
        # radarr should NOT appear in the command portion
        # Grab the 'Command:' line only
        cmd_line = [l for l in out.splitlines() if l.startswith("Command:")][0]
        assert "radarr" not in cmd_line

    def test_unknown_service_returns_error_code(self, compose_file):
        rc = main(["--file", compose_file, "--env-file", "my.env", "--services", "nonexistent"])
        assert rc == 1

    def test_unknown_service_prints_error_message(self, compose_file, capsys):
        main(["--file", compose_file, "--env-file", "my.env", "--services", "nonexistent"])
        assert "nonexistent" in capsys.readouterr().out

    def test_missing_compose_file_returns_error_code(self):
        rc = main(["--file", "/nonexistent.yml", "--env-file", "my.env", "--all"])
        assert rc == 1

    def test_no_selection_returns_zero(self, compose_file):
        with patch("builtins.input", return_value="none"):
            rc = main(["--file", compose_file, "--env-file", "my.env"])
        assert rc == 0

    def test_run_flag_calls_run_command(self, compose_file):
        with patch("select_containers.run_command", return_value=0) as mock_run:
            main(["--file", compose_file, "--env-file", "my.env", "--all", "--run"])
        mock_run.assert_called_once()

    def test_run_flag_passes_selected_services_to_command(self, compose_file):
        captured = []

        def fake_run(cmd):
            captured.extend(cmd)
            return 0

        with patch("select_containers.run_command", side_effect=fake_run):
            main(
                [
                    "--file",
                    compose_file,
                    "--env-file",
                    "my.env",
                    "--services",
                    "sonarr,radarr",
                    "--run",
                ]
            )

        assert "sonarr" in captured
        assert "radarr" in captured
        assert "plex" not in captured
        assert "sabnzbd" not in captured

    def test_run_flag_forwards_exit_code(self, compose_file):
        with patch("select_containers.run_command", return_value=42):
            rc = main(["--file", compose_file, "--env-file", "my.env", "--all", "--run"])
        assert rc == 42

    def test_build_flag_passed_to_compose_command(self, compose_file):
        captured = []

        def fake_run(cmd):
            captured.extend(cmd)
            return 0

        with patch("select_containers.run_command", side_effect=fake_run):
            main(
                [
                    "--file",
                    compose_file,
                    "--env-file",
                    "my.env",
                    "--all",
                    "--build",
                    "--run",
                ]
            )

        assert "--build" in captured

    def test_compose_file_arg_used_in_command(self, compose_file, capsys):
        main(["--file", compose_file, "--env-file", "my.env", "--all"])
        out = capsys.readouterr().out
        assert compose_file in out

    def test_env_file_arg_used_in_command(self, compose_file, capsys):
        main(["--file", compose_file, "--env-file", "custom.env", "--all"])
        out = capsys.readouterr().out
        assert "custom.env" in out
