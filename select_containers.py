#!/usr/bin/env python3
"""
select_containers.py - Config-driven container selection for Docker Compose.

The canonical list of which services should run is stored in services.yml.
Every spin-up reads that file; services marked false are never passed to
docker compose and therefore can never be pulled or started.

Modes:
    (default)    Read services.yml and print the docker compose command (dry-run).
    --run        Read services.yml and execute docker compose up.
    --init       Generate services.yml from the compose file (all enabled).
                 Safe to re-run: adds new services, preserves existing values.
    --edit       Interactive toggle UI to enable/disable services, then save.

Usage:
    python select_containers.py [options]

Options:
    --config FILE       Path to services config (default: services.yml)
    --file FILE         Path to Docker Compose file (default: htpcServices.yml)
    --env-file FILE     Path to env file (default: HTPC/HTPC_envValues.env)
    --run               Execute docker compose up (default: dry-run)
    --init              (Re-)generate services.yml from the compose file
    --edit              Interactively toggle services and save to services.yml
    --build             Pass --build flag to docker compose up
"""

import argparse
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Error: PyYAML is required. Install it with: pip install pyyaml")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Compose file helpers
# ---------------------------------------------------------------------------


def parse_services(compose_file: str) -> list:
    """Parse service names from a Docker Compose YAML file.

    Args:
        compose_file: Path to the docker-compose YAML file.

    Returns:
        List of service name strings.

    Raises:
        FileNotFoundError: If the compose file does not exist.
    """
    path = Path(compose_file)
    if not path.exists():
        raise FileNotFoundError(f"Compose file not found: {compose_file}")

    with open(path) as f:
        config = yaml.safe_load(f)

    if not config or "services" not in config:
        return []

    return list(config["services"].keys())


# ---------------------------------------------------------------------------
# Config file helpers
# ---------------------------------------------------------------------------


def load_config(config_file: str) -> dict:
    """Load the services config from a YAML file.

    Args:
        config_file: Path to the services config YAML file.

    Returns:
        Dict mapping service name (str) to enabled flag (bool).

    Raises:
        FileNotFoundError: If the config file does not exist.
        ValueError: If the file is not a valid key->bool mapping.
    """
    path = Path(config_file)
    if not path.exists():
        raise FileNotFoundError(
            f"Config file not found: {config_file}\n"
            "Run with --init to generate it from your compose file."
        )

    with open(path) as f:
        data = yaml.safe_load(f)

    if data is None:
        return {}

    if not isinstance(data, dict):
        raise ValueError(f"Config file must be a YAML mapping, got: {type(data).__name__}")

    invalid = {k: v for k, v in data.items() if not isinstance(v, bool)}
    if invalid:
        raise ValueError(
            f"All values in {config_file} must be true or false. "
            f"Invalid entries: {invalid}"
        )

    return data


def save_config(config_file: str, config: dict) -> None:
    """Write the services config dict to a YAML file.

    Args:
        config_file: Path to write the YAML config.
        config: Dict mapping service name (str) to enabled flag (bool).
    """
    with open(config_file, "w") as f:
        f.write("# services.yml - Set to true to enable a service, false to disable it.\n")
        f.write("# This file is read on every docker compose up.\n")
        f.write("# Services marked false will never be pulled or started.\n\n")
        yaml.dump(config, f, default_flow_style=False, sort_keys=True)


def init_config(config_file: str, available: list) -> dict:
    """Create or update services.yml from the list of available services.

    Existing entries are preserved; new services are added as enabled (true).

    Args:
        config_file: Path to the services config YAML file.
        available: List of service name strings from the compose file.

    Returns:
        The resulting config dict.
    """
    try:
        existing = load_config(config_file)
    except FileNotFoundError:
        existing = {}

    merged = {svc: existing.get(svc, True) for svc in available}
    save_config(config_file, merged)
    return merged


def get_enabled_services(config: dict, available: list) -> list:
    """Return the subset of available services that are enabled in config.

    Services present in the compose file but missing from the config are
    treated as disabled (fail-safe: unknown == off).

    Args:
        config: Dict mapping service name to bool.
        available: Ordered list of service names from the compose file.

    Returns:
        List of enabled service name strings, preserving compose-file order.
    """
    return [svc for svc in available if config.get(svc, False)]


# ---------------------------------------------------------------------------
# Interactive edit
# ---------------------------------------------------------------------------


def interactive_edit(config: dict, services: list) -> dict:
    """Present a toggle UI to enable/disable services and return updated config.

    Args:
        config: Current config dict (service -> bool).
        services: Ordered list of all known service names.

    Returns:
        Updated config dict, or the original dict if the user cancels.
    """
    if not services:
        return config

    current = {svc: config.get(svc, True) for svc in services}

    while True:
        print("\nServices  (* = enabled,   - = disabled):")
        for i, svc in enumerate(services, 1):
            marker = "*" if current[svc] else "-"
            print(f"  [{i:2d}] [{marker}] {svc}")

        print("\nEnter a number to toggle, 'save' to save and exit, or 'cancel' to discard:")

        try:
            raw = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return config

        if raw == "save":
            return current

        if raw == "cancel":
            return config

        if raw.isdigit():
            idx = int(raw)
            if 1 <= idx <= len(services):
                svc = services[idx - 1]
                current[svc] = not current[svc]
                state = "enabled" if current[svc] else "disabled"
                print(f"  {svc} -> {state}")
            else:
                print(f"  Number {idx} is out of range (1-{len(services)}).")
        else:
            print("  Enter a number, 'save', or 'cancel'.")


# ---------------------------------------------------------------------------
# Docker Compose helpers
# ---------------------------------------------------------------------------


def build_compose_command(
    compose_file: str,
    env_file: str,
    services: list,
    detach: bool = True,
    build: bool = False,
) -> list:
    """Build a docker compose up command for the given services.

    Args:
        compose_file: Path to the docker-compose YAML file.
        env_file: Path to the environment variables file.
        services: List of service names to include in the command.
        detach: Whether to pass -d (detached mode) flag.
        build: Whether to pass --build flag to rebuild images.

    Returns:
        List of command tokens suitable for subprocess.run().
    """
    cmd = ["docker", "compose", "-f", compose_file, "--env-file", env_file, "up"]
    if detach:
        cmd.append("-d")
    if build:
        cmd.append("--build")
    cmd.extend(services)
    return cmd


def run_command(command: list) -> int:
    """Execute a command and return the exit code.

    Args:
        command: List of command tokens.

    Returns:
        Process exit code.
    """
    result = subprocess.run(command)
    return result.returncode


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Config-driven container selection for Docker Compose.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--config",
        default="services.yml",
        help="Path to the services config file (default: services.yml)",
    )
    parser.add_argument(
        "--file",
        default="htpcServices.yml",
        help="Path to the Docker Compose file (default: htpcServices.yml)",
    )
    parser.add_argument(
        "--env-file",
        default="HTPC/HTPC_envValues.env",
        help="Path to the env file (default: HTPC/HTPC_envValues.env)",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Execute docker compose up (default: dry-run, prints command only)",
    )
    parser.add_argument(
        "--init",
        action="store_true",
        help="Generate/update services.yml from the compose file, then exit",
    )
    parser.add_argument(
        "--edit",
        action="store_true",
        help="Interactively toggle services and save to services.yml",
    )
    parser.add_argument(
        "--build",
        action="store_true",
        help="Rebuild images before starting containers",
    )
    args = parser.parse_args(argv)

    # Parse available services from compose file
    try:
        available = parse_services(args.file)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1

    if not available:
        print("No services found in compose file.")
        return 1

    # --init: generate/update config and exit
    if args.init:
        config = init_config(args.config, available)
        enabled = sum(1 for v in config.values() if v)
        print(f"Wrote {args.config} ({enabled}/{len(config)} services enabled).")
        return 0

    # --edit: interactive toggle, save, then exit
    if args.edit:
        try:
            config = load_config(args.config)
        except (FileNotFoundError, ValueError) as e:
            print(f"Error: {e}")
            return 1
        updated = interactive_edit(config, available)
        if updated is not config:
            save_config(args.config, updated)
            enabled = sum(1 for v in updated.values() if v)
            print(f"Saved {args.config} ({enabled}/{len(updated)} services enabled).")
        else:
            print("No changes saved.")
        return 0

    # Default / --run: read config and start enabled services
    try:
        config = load_config(args.config)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}")
        return 1

    selected = get_enabled_services(config, available)

    if not selected:
        print("No services are enabled in services.yml. Nothing to start.")
        return 0

    cmd = build_compose_command(args.file, args.env_file, selected, build=args.build)
    print(f"Enabled services ({len(selected)}/{len(available)}): {', '.join(selected)}")
    print(f"\nCommand: {' '.join(cmd)}")

    if args.run:
        print("Starting services...")
        return run_command(cmd)
    else:
        print("\n(Dry-run mode. Use --run to execute.)")
        return 0


if __name__ == "__main__":
    sys.exit(main())
