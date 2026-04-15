#!/usr/bin/env python3
"""
select_containers.py - Interactively select which containers to start.

Usage:
    python select_containers.py [options]

Options:
    --file FILE         Path to Docker Compose file (default: htpcServices.yml)
    --env-file FILE     Path to env file (default: HTPC/HTPC_envValues.env)
    --run               Execute docker compose (default: dry-run, prints command only)
    --all               Start all services without prompting
    --services s1,s2    Comma-separated list of services to start (non-interactive)
    --build             Pass --build flag to docker compose up

Notes:
    Services with 'depends_on' dependencies will have those dependencies started
    automatically by Docker Compose, even if not explicitly selected.
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


def interactive_select(services: list) -> list:
    """Present an interactive numbered checklist and return the selected services.

    Args:
        services: List of available service name strings.

    Returns:
        List of selected service name strings (empty list if none selected or cancelled).
    """
    if not services:
        return []

    print("\nAvailable services:")
    for i, svc in enumerate(services, 1):
        print(f"  [{i:2d}] {svc}")

    print("\nEnter service numbers separated by commas (e.g. 1,3,5),")
    print("'all' to select all, or 'none' / Enter to cancel:")

    while True:
        try:
            raw = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return []

        if raw == "all":
            return list(services)

        if raw in ("none", ""):
            return []

        selected = []
        valid = True
        for part in raw.split(","):
            part = part.strip()
            if not part.isdigit():
                print(f"  Invalid input: '{part}'. Enter numbers, 'all', or 'none'.")
                valid = False
                break
            idx = int(part)
            if idx < 1 or idx > len(services):
                print(f"  Number {idx} is out of range (1-{len(services)}).")
                valid = False
                break
            service = services[idx - 1]
            if service not in selected:
                selected.append(service)

        if valid:
            return selected


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
    """Execute a shell command and return the exit code.

    Args:
        command: List of command tokens.

    Returns:
        Process exit code.
    """
    result = subprocess.run(command)
    return result.returncode


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Interactively select Docker containers to start.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
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
        "--all",
        action="store_true",
        dest="select_all",
        help="Start all services without prompting",
    )
    parser.add_argument(
        "--services",
        help="Comma-separated list of services to start (non-interactive)",
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

    # Determine selected services
    if args.select_all:
        selected = list(available)
    elif args.services:
        requested = [s.strip() for s in args.services.split(",")]
        unknown = [s for s in requested if s not in available]
        if unknown:
            print(f"Error: Unknown service(s): {', '.join(unknown)}")
            print(f"Available: {', '.join(available)}")
            return 1
        selected = requested
    else:
        selected = interactive_select(available)

    if not selected:
        print("No services selected. Exiting.")
        return 0

    # Build and optionally run the command
    cmd = build_compose_command(
        args.file, args.env_file, selected, build=args.build
    )
    print(f"\nCommand: {' '.join(cmd)}")

    if args.run:
        print("Starting selected services...")
        return run_command(cmd)
    else:
        print("\n(Dry-run mode. Use --run to execute.)")
        return 0


if __name__ == "__main__":
    sys.exit(main())
