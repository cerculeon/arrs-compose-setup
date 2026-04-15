"""
Tests for select_containers.py

Run with:
    pytest tests/test_select_containers.py -v
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from select_containers import (
    parse_services,
    load_config,
    save_config,
    init_config,
    get_enabled_services,
    interactive_edit,
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
SERVICE_NAMES = list(SAMPLE_SERVICES.keys())

SAMPLE_COMPOSE = {"services": SAMPLE_SERVICES}


@pytest.fixture
def compose_file(tmp_path):
    f = tmp_path / "test-compose.yml"
    f.write_text(yaml.dump(SAMPLE_COMPOSE))
    return str(f)


@pytest.fixture
def config_file(tmp_path):
    """A config file with all services enabled."""
    f = tmp_path / "services.yml"
    data = {svc: True for svc in SERVICE_NAMES}
    f.write_text(yaml.dump(data))
    return str(f)


@pytest.fixture
def partial_config_file(tmp_path):
    """A config file with some services disabled."""
    f = tmp_path / "services.yml"
    data = {"sabnzbd": True, "sonarr": False, "radarr": True, "plex": False}
    f.write_text(yaml.dump(data))
    return str(f)


# ---------------------------------------------------------------------------
# parse_services
# ---------------------------------------------------------------------------


class TestParseServices:
    def test_returns_all_service_names(self, compose_file):
        assert set(parse_services(compose_file)) == set(SERVICE_NAMES)

    def test_returns_list_type(self, compose_file):
        assert isinstance(parse_services(compose_file), list)

    def test_correct_service_count(self, compose_file):
        assert len(parse_services(compose_file)) == len(SERVICE_NAMES)

    def test_missing_file_raises_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            parse_services("/nonexistent/compose.yml")

    def test_no_services_key_returns_empty(self, tmp_path):
        f = tmp_path / "empty.yml"
        f.write_text(yaml.dump({"version": "3"}))
        assert parse_services(str(f)) == []

    def test_single_service(self, tmp_path):
        f = tmp_path / "single.yml"
        f.write_text(yaml.dump({"services": {"plex": {"image": "linuxserver/plex"}}}))
        assert parse_services(str(f)) == ["plex"]


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------


class TestLoadConfig:
    def test_loads_all_true_config(self, config_file):
        config = load_config(config_file)
        assert all(v is True for v in config.values())

    def test_loads_mixed_config(self, partial_config_file):
        config = load_config(partial_config_file)
        assert config["sabnzbd"] is True
        assert config["sonarr"] is False

    def test_returns_dict(self, config_file):
        assert isinstance(load_config(config_file), dict)

    def test_missing_file_raises_file_not_found(self):
        with pytest.raises(FileNotFoundError, match="--init"):
            load_config("/nonexistent/services.yml")

    def test_non_bool_values_raise_value_error(self, tmp_path):
        f = tmp_path / "bad.yml"
        f.write_text(yaml.dump({"plex": "yes"}))
        with pytest.raises(ValueError, match="true or false"):
            load_config(str(f))

    def test_non_mapping_raises_value_error(self, tmp_path):
        f = tmp_path / "list.yml"
        f.write_text("- plex\n- sonarr\n")
        with pytest.raises(ValueError):
            load_config(str(f))

    def test_empty_file_returns_empty_dict(self, tmp_path):
        f = tmp_path / "empty.yml"
        f.write_text("")
        assert load_config(str(f)) == {}

    def test_service_names_preserved(self, config_file):
        config = load_config(config_file)
        for svc in SERVICE_NAMES:
            assert svc in config


# ---------------------------------------------------------------------------
# save_config
# ---------------------------------------------------------------------------


class TestSaveConfig:
    def test_file_is_created(self, tmp_path):
        f = tmp_path / "out.yml"
        save_config(str(f), {"plex": True})
        assert f.exists()

    def test_roundtrip_all_true(self, tmp_path):
        f = tmp_path / "out.yml"
        data = {svc: True for svc in SERVICE_NAMES}
        save_config(str(f), data)
        assert load_config(str(f)) == data

    def test_roundtrip_mixed(self, tmp_path):
        f = tmp_path / "out.yml"
        data = {"sabnzbd": True, "plex": False, "sonarr": True}
        save_config(str(f), data)
        assert load_config(str(f)) == data

    def test_file_contains_comment(self, tmp_path):
        f = tmp_path / "out.yml"
        save_config(str(f), {"plex": True})
        assert "services.yml" in f.read_text()

    def test_overwrites_existing_file(self, tmp_path):
        f = tmp_path / "out.yml"
        save_config(str(f), {"plex": True})
        save_config(str(f), {"plex": False})
        assert load_config(str(f)) == {"plex": False}


# ---------------------------------------------------------------------------
# init_config
# ---------------------------------------------------------------------------


class TestInitConfig:
    def test_creates_config_when_missing(self, tmp_path):
        f = tmp_path / "services.yml"
        init_config(str(f), SERVICE_NAMES)
        assert f.exists()

    def test_all_services_enabled_by_default(self, tmp_path):
        f = tmp_path / "services.yml"
        config = init_config(str(f), SERVICE_NAMES)
        assert all(config[svc] is True for svc in SERVICE_NAMES)

    def test_new_service_added_as_enabled(self, partial_config_file):
        config = init_config(partial_config_file, SERVICE_NAMES + ["newservice"])
        assert config["newservice"] is True

    def test_existing_disabled_value_preserved(self, partial_config_file):
        config = init_config(partial_config_file, SERVICE_NAMES)
        assert config["sonarr"] is False

    def test_existing_enabled_value_preserved(self, partial_config_file):
        config = init_config(partial_config_file, SERVICE_NAMES)
        assert config["sabnzbd"] is True

    def test_services_not_in_available_dropped(self, tmp_path):
        f = tmp_path / "services.yml"
        # Pre-populate with a service not in available
        f.write_text(yaml.dump({"ghost_service": True, "plex": True}))
        config = init_config(str(f), ["plex", "sonarr"])
        assert "ghost_service" not in config

    def test_returns_dict(self, tmp_path):
        f = tmp_path / "services.yml"
        result = init_config(str(f), SERVICE_NAMES)
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# get_enabled_services
# ---------------------------------------------------------------------------


class TestGetEnabledServices:
    def test_all_enabled_returns_all(self):
        config = {svc: True for svc in SERVICE_NAMES}
        assert get_enabled_services(config, SERVICE_NAMES) == SERVICE_NAMES

    def test_all_disabled_returns_empty(self):
        config = {svc: False for svc in SERVICE_NAMES}
        assert get_enabled_services(config, SERVICE_NAMES) == []

    def test_mixed_returns_only_enabled(self):
        config = {"sabnzbd": True, "sonarr": False, "radarr": True, "plex": False}
        result = get_enabled_services(config, SERVICE_NAMES)
        assert "sabnzbd" in result
        assert "radarr" in result
        assert "sonarr" not in result
        assert "plex" not in result

    def test_preserves_compose_file_order(self):
        order = ["plex", "sonarr", "sabnzbd"]
        config = {svc: True for svc in order}
        result = get_enabled_services(config, order)
        assert result == order

    def test_service_missing_from_config_is_excluded(self):
        # Fail-safe: unknown == off
        config = {"sabnzbd": True}
        result = get_enabled_services(config, ["sabnzbd", "plex"])
        assert "plex" not in result

    def test_empty_available_returns_empty(self):
        assert get_enabled_services({"plex": True}, []) == []

    def test_empty_config_returns_empty(self):
        assert get_enabled_services({}, SERVICE_NAMES) == []


# ---------------------------------------------------------------------------
# interactive_edit
# ---------------------------------------------------------------------------


class TestInteractiveEdit:
    def test_save_returns_updated_config(self):
        config = {"plex": True, "sonarr": True}
        # Toggle sonarr off, then save
        with patch("builtins.input", side_effect=["2", "save"]):
            result = interactive_edit(config, ["plex", "sonarr"])
        assert result["sonarr"] is False
        assert result["plex"] is True

    def test_cancel_returns_original_config(self):
        config = {"plex": True, "sonarr": True}
        with patch("builtins.input", side_effect=["2", "cancel"]):
            result = interactive_edit(config, ["plex", "sonarr"])
        assert result is config

    def test_toggle_enables_disabled_service(self):
        config = {"plex": False}
        with patch("builtins.input", side_effect=["1", "save"]):
            result = interactive_edit(config, ["plex"])
        assert result["plex"] is True

    def test_toggle_disables_enabled_service(self):
        config = {"plex": True}
        with patch("builtins.input", side_effect=["1", "save"]):
            result = interactive_edit(config, ["plex"])
        assert result["plex"] is False

    def test_double_toggle_restores_original(self):
        config = {"plex": True}
        with patch("builtins.input", side_effect=["1", "1", "save"]):
            result = interactive_edit(config, ["plex"])
        assert result["plex"] is True

    def test_empty_services_returns_config_unchanged(self):
        config = {"plex": True}
        result = interactive_edit(config, [])
        assert result is config

    def test_out_of_range_number_does_not_change_config(self):
        config = {"plex": True}
        with patch("builtins.input", side_effect=["99", "save"]):
            result = interactive_edit(config, ["plex"])
        assert result["plex"] is True

    def test_invalid_text_is_ignored(self):
        config = {"plex": True}
        with patch("builtins.input", side_effect=["bad", "save"]):
            result = interactive_edit(config, ["plex"])
        assert result["plex"] is True

    def test_keyboard_interrupt_returns_original(self):
        config = {"plex": True}
        with patch("builtins.input", side_effect=KeyboardInterrupt):
            result = interactive_edit(config, ["plex"])
        assert result is config

    def test_eof_returns_original(self):
        config = {"plex": True}
        with patch("builtins.input", side_effect=EOFError):
            result = interactive_edit(config, ["plex"])
        assert result is config

    def test_service_missing_from_config_defaults_to_enabled(self):
        # A service in 'available' but not yet in config should start as True
        config = {}
        with patch("builtins.input", return_value="save"):
            result = interactive_edit(config, ["plex"])
        assert result["plex"] is True


# ---------------------------------------------------------------------------
# build_compose_command
# ---------------------------------------------------------------------------


class TestBuildComposeCommand:
    def test_starts_with_docker_compose(self):
        cmd = build_compose_command("f.yml", "e.env", ["plex"])
        assert cmd[:2] == ["docker", "compose"]

    def test_includes_compose_file_flag(self):
        cmd = build_compose_command("myfile.yml", "e.env", ["plex"])
        idx = cmd.index("-f")
        assert cmd[idx + 1] == "myfile.yml"

    def test_includes_env_file_flag(self):
        cmd = build_compose_command("f.yml", "my.env", ["plex"])
        idx = cmd.index("--env-file")
        assert cmd[idx + 1] == "my.env"

    def test_includes_up_subcommand(self):
        assert "up" in build_compose_command("f.yml", "e.env", ["plex"])

    def test_detach_flag_included_by_default(self):
        assert "-d" in build_compose_command("f.yml", "e.env", ["plex"])

    def test_detach_flag_omitted_when_false(self):
        assert "-d" not in build_compose_command("f.yml", "e.env", ["plex"], detach=False)

    def test_build_flag_omitted_by_default(self):
        assert "--build" not in build_compose_command("f.yml", "e.env", ["plex"])

    def test_build_flag_included_when_true(self):
        assert "--build" in build_compose_command("f.yml", "e.env", ["plex"], build=True)

    def test_services_appended(self):
        cmd = build_compose_command("f.yml", "e.env", ["sonarr", "radarr"])
        assert "sonarr" in cmd
        assert "radarr" in cmd

    def test_services_appear_once_each(self):
        cmd = build_compose_command("f.yml", "e.env", ["sonarr", "radarr"])
        assert cmd.count("sonarr") == 1

    def test_returns_list_of_strings(self):
        cmd = build_compose_command("f.yml", "e.env", ["plex"])
        assert isinstance(cmd, list)
        assert all(isinstance(t, str) for t in cmd)


# ---------------------------------------------------------------------------
# run_command
# ---------------------------------------------------------------------------


class TestRunCommand:
    def test_returns_zero_on_success(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            assert run_command(["echo", "hi"]) == 0

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
# main - --init mode
# ---------------------------------------------------------------------------


class TestMainInit:
    def test_returns_zero(self, compose_file, tmp_path):
        cfg = str(tmp_path / "services.yml")
        assert main(["--init", "--file", compose_file, "--config", cfg]) == 0

    def test_creates_config_file(self, compose_file, tmp_path):
        cfg = str(tmp_path / "services.yml")
        main(["--init", "--file", compose_file, "--config", cfg])
        assert Path(cfg).exists()

    def test_all_services_enabled(self, compose_file, tmp_path):
        cfg = str(tmp_path / "services.yml")
        main(["--init", "--file", compose_file, "--config", cfg])
        config = load_config(cfg)
        for svc in SERVICE_NAMES:
            assert config[svc] is True

    def test_preserves_existing_disabled(self, compose_file, partial_config_file):
        main(["--init", "--file", compose_file, "--config", partial_config_file])
        config = load_config(partial_config_file)
        assert config["sonarr"] is False

    def test_prints_summary(self, compose_file, tmp_path, capsys):
        cfg = str(tmp_path / "services.yml")
        main(["--init", "--file", compose_file, "--config", cfg])
        assert "services.yml" in capsys.readouterr().out

    def test_missing_compose_file_returns_error(self, tmp_path):
        cfg = str(tmp_path / "services.yml")
        assert main(["--init", "--file", "/nonexistent.yml", "--config", cfg]) == 1


# ---------------------------------------------------------------------------
# main - --edit mode
# ---------------------------------------------------------------------------


class TestMainEdit:
    def test_returns_zero_on_save(self, compose_file, config_file):
        with patch("builtins.input", return_value="save"):
            rc = main(["--edit", "--file", compose_file, "--config", config_file])
        assert rc == 0

    def test_saves_changes(self, compose_file, config_file):
        # parse_services reads the compose file written by yaml.dump, which sorts keys
        # alphabetically, so the UI order is the sorted order of SERVICE_NAMES.
        first_in_ui = sorted(SERVICE_NAMES)[0]
        with patch("builtins.input", side_effect=["1", "save"]):
            main(["--edit", "--file", compose_file, "--config", config_file])
        config = load_config(config_file)
        assert config[first_in_ui] is False

    def test_cancel_does_not_save_changes(self, compose_file, config_file):
        original = load_config(config_file)
        with patch("builtins.input", side_effect=["1", "cancel"]):
            main(["--edit", "--file", compose_file, "--config", config_file])
        assert load_config(config_file) == original

    def test_missing_config_returns_error(self, compose_file, tmp_path):
        cfg = str(tmp_path / "missing.yml")
        rc = main(["--edit", "--file", compose_file, "--config", cfg])
        assert rc == 1

    def test_prints_saved_message(self, compose_file, config_file, capsys):
        with patch("builtins.input", side_effect=["1", "save"]):
            main(["--edit", "--file", compose_file, "--config", config_file])
        assert "Saved" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# main - default / --run mode
# ---------------------------------------------------------------------------


class TestMainRun:
    def test_dry_run_returns_zero(self, compose_file, config_file):
        assert main(["--file", compose_file, "--config", config_file]) == 0

    def test_dry_run_prints_dry_run_notice(self, compose_file, config_file, capsys):
        main(["--file", compose_file, "--config", config_file])
        assert "Dry-run" in capsys.readouterr().out

    def test_dry_run_does_not_call_subprocess(self, compose_file, config_file):
        with patch("select_containers.run_command") as mock_run:
            main(["--file", compose_file, "--config", config_file])
        mock_run.assert_not_called()

    def test_enabled_services_appear_in_command_output(self, compose_file, config_file, capsys):
        main(["--file", compose_file, "--config", config_file])
        out = capsys.readouterr().out
        for svc in SERVICE_NAMES:
            assert svc in out

    def test_disabled_service_excluded_from_command(self, compose_file, partial_config_file, capsys):
        main(["--file", compose_file, "--config", partial_config_file])
        cmd_line = [l for l in capsys.readouterr().out.splitlines() if l.startswith("Command:")][0]
        assert "sonarr" not in cmd_line
        assert "plex" not in cmd_line

    def test_disabled_service_included_in_enabled_services_line(self, compose_file, partial_config_file, capsys):
        # The "Enabled services" summary line should only list enabled ones
        main(["--file", compose_file, "--config", partial_config_file])
        summary = [l for l in capsys.readouterr().out.splitlines() if l.startswith("Enabled")][0]
        assert "sabnzbd" in summary
        assert "sonarr" not in summary

    def test_all_disabled_exits_cleanly(self, compose_file, tmp_path):
        cfg = tmp_path / "services.yml"
        cfg.write_text(yaml.dump({svc: False for svc in SERVICE_NAMES}))
        rc = main(["--file", compose_file, "--config", str(cfg)])
        assert rc == 0

    def test_missing_config_returns_error(self, compose_file, tmp_path):
        cfg = str(tmp_path / "missing.yml")
        assert main(["--file", compose_file, "--config", cfg]) == 1

    def test_run_flag_calls_run_command(self, compose_file, config_file):
        with patch("select_containers.run_command", return_value=0) as mock_run:
            main(["--file", compose_file, "--config", config_file, "--run"])
        mock_run.assert_called_once()

    def test_run_flag_only_passes_enabled_services(self, compose_file, partial_config_file):
        captured = []

        def fake_run(cmd):
            captured.extend(cmd)
            return 0

        with patch("select_containers.run_command", side_effect=fake_run):
            main(["--file", compose_file, "--config", partial_config_file, "--run"])

        assert "sabnzbd" in captured
        assert "radarr" in captured
        assert "sonarr" not in captured
        assert "plex" not in captured

    def test_run_flag_forwards_exit_code(self, compose_file, config_file):
        with patch("select_containers.run_command", return_value=42):
            rc = main(["--file", compose_file, "--config", config_file, "--run"])
        assert rc == 42

    def test_build_flag_passed_through(self, compose_file, config_file):
        captured = []

        def fake_run(cmd):
            captured.extend(cmd)
            return 0

        with patch("select_containers.run_command", side_effect=fake_run):
            main(["--file", compose_file, "--config", config_file, "--run", "--build"])

        assert "--build" in captured

    def test_env_file_arg_used_in_command(self, compose_file, config_file, capsys):
        main(["--file", compose_file, "--config", config_file, "--env-file", "custom.env"])
        assert "custom.env" in capsys.readouterr().out


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


