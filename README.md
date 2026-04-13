# HTPC Config

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Contributions Welcome](https://img.shields.io/badge/Contributions-Welcome-brightgreen.svg)](CONTRIBUTING.md)

Docker Compose based Home Theater PC stack with optional observability services.

This repository contains two related stacks:

- HTPC media services (downloaders, indexers, media managers, and media servers)
- Observability services (Elasticsearch, Kibana, Portainer)

The repository is designed for self-hosted environments and can be adapted to your own paths, network, and host layout.

## Table of Contents

- [What This Repo Provides](#what-this-repo-provides)
- [Repository Layout](#repository-layout)
- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Running the Stacks](#running-the-stacks)
- [Service Reference](#service-reference)
- [Observability Notes](#observability-notes)
- [Troubleshooting](#troubleshooting)
- [Security and Public Repo Guidance](#security-and-public-repo-guidance)
- [Contributing](#contributing)
- [Roadmap Ideas](#roadmap-ideas)
- [License](#license)
- [Security](#security)

## What This Repo Provides

The HTPC stack in [htpcServices.yml](htpcServices.yml) includes:

- SABnzbd
- Transmission
- Prowlarr
- Radarr
- Sonarr
- Mylar3
- Readarr
- Plex
- Jellyfin
- Emby
- Tautulli
- Overseerr
- FlareSolverr
- Filebeat
- Metricbeat

The observability stack in [observabilityServices.yml](observabilityServices.yml) includes:

- Elasticsearch
- Kibana
- Portainer

## Repository Layout

```text
.
├── htpcServices.yml
├── observabilityServices.yml
├── runHTPCStack.sh
├── runObserverStack.sh
├── HTPC/
│   └── HTPC_envValues.env
├── OBSERVER/
│   └── OBSERVER_envValues.env
├── filebeat/
│   └── filebeat.yml
└── metricbeat/
	 ├── metricbeat.yml
	 └── modules.d/
		  └── docker.yml
```

## Architecture Overview

- The HTPC compose file defines most media services on a custom bridge network named htpc_net with static container IP assignments.
- Plex runs in host networking mode.
- Filebeat and Metricbeat run on the HTPC host and ship logs/metrics to Elasticsearch/Kibana.
- Elasticsearch/Kibana/Portainer are defined as a separate compose stack intended to run independently.

Typical deployment pattern:

1. Host A: HTPC stack from [htpcServices.yml](htpcServices.yml)
2. Host B: Observability stack from [observabilityServices.yml](observabilityServices.yml)

You can also co-locate both stacks if your host has sufficient resources and networking is adjusted.

## Prerequisites

- Linux host(s) with Docker Engine installed
- Docker Compose plugin (docker compose) or legacy docker-compose binary
- Storage mounts for media and downloads
- A user/group mapping for container permissions (PUID/PGID values)
- Open ports according to your desired service exposure

Optional but recommended:

- Reverse proxy and TLS for internet-exposed access
- Firewall rules restricting management interfaces
- Backup strategy for configuration volumes

## Quick Start

1. Clone the repo.
2. Copy and customize env files:
    - [HTPC/HTPC_envValues.env](HTPC/HTPC_envValues.env)
    - [OBSERVER/OBSERVER_envValues.env](OBSERVER/OBSERVER_envValues.env)
    - Use the provided templates: [HTPC/HTPC_envValues.env.example](HTPC/HTPC_envValues.env.example) and [OBSERVER/OBSERVER_envValues.env.example](OBSERVER/OBSERVER_envValues.env.example) removing the .example
3. Validate configuration (without starting containers):

```bash
./runHTPCStack.sh
./runObserverStack.sh
```

4. Start stacks:
 Note:  you may need to run as root depending on your docker setup. if you get "permission denied while trying to connect to the docker API" then you should rerun as the root user

```bash
./runHTPCStack.sh yes
./runObserverStack.sh yes
```

5. Open service UIs (examples):
    - Sonarr: http://<host>:8989
    - Radarr: http://<host>:7878
    - Prowlarr: http://<host>:9696
    - SABnzbd: http://<host>:8088
    - Transmission: http://<host>:9091
    - Jellyfin: http://<host>:8096
    - Emby: http://<host>:8099

6. Fix Beats config file ownership (required or Beats containers will exit on start):

```bash
sudo chown root:root filebeat/filebeat.yml
sudo chown root:root metricbeat/metricbeat.yml
sudo chmod go-w filebeat/filebeat.yml
sudo chmod go-w metricbeat/metricbeat.yml
docker restart filebeat metricbeat
```

See [Beats config file ownership error](#beats-config-file-ownership-error) in Troubleshooting if the containers still fail to start.
    - Kibana: http://<observer-host>:5601
    - Elasticsearch API: http://<observer-host>:9200
    - Portainer: http://<observer-host>:9191

## Configuration

### HTPC Env Variables

Defined in [HTPC/HTPC_envValues.env](HTPC/HTPC_envValues.env):

- MOVIE_FOLDER
- TV_FOLDER
- INCOMPLETE_DOWNLOADS
- COMPLETE_DOWNLOADS
- WATCH_FOLDER
- EBOOK_FOLDER
- COMIC_FOLDER
- CONFIG_ROOT
- KIBANA_HOST
- BEATS_HOST
- HTPC_DOCKER_COMPOSE_ROOT

Update these to your filesystem and network.

You can start from [HTPC/HTPC_envValues.env.example](HTPC/HTPC_envValues.env.example).

### Observer Env Variables

Defined in [OBSERVER/OBSERVER_envValues.env](OBSERVER/OBSERVER_envValues.env):

- CONFIG_ROOT
- KIBANA_HOST_IP
- BEATS_HOST

You can start from [OBSERVER/OBSERVER_envValues.env.example](OBSERVER/OBSERVER_envValues.env.example).

### Beats Config

- Filebeat config: [filebeat/filebeat.yml](filebeat/filebeat.yml)
- Metricbeat config: [metricbeat/metricbeat.yml](metricbeat/metricbeat.yml)
- Metricbeat Docker module: [metricbeat/modules.d/docker.yml](metricbeat/modules.d/docker.yml)

> **Important:** Both Beats config files contain hardcoded IP addresses that must be changed before the stack will work.
> Each address is marked with a `# CHANGE THIS` comment directly in the file.
> Search for `CHANGE THIS` in [filebeat/filebeat.yml](filebeat/filebeat.yml) and [metricbeat/metricbeat.yml](metricbeat/metricbeat.yml) and replace the IPs with those of your own Elasticsearch and Kibana hosts.

Additional notes:

- The Beats config volume mounts use `${HTPC_DOCKER_COMPOSE_ROOT}` to locate config files. Set this variable in [HTPC/HTPC_envValues.env](HTPC/HTPC_envValues.env) to the absolute path of your local clone.

### Beats ILM rollover policies

Both Filebeat and Metricbeat use custom ILM policy files mounted into their containers:

- Filebeat policy: [filebeat/filebeat-ilm.json](filebeat/filebeat-ilm.json)
- Metricbeat policy: [metricbeat/metricbeat-ilm.json](metricbeat/metricbeat-ilm.json)

Current rollover and retention behavior is the same for both Beats:

- Rollover when an index reaches `1gb` or `1d`, whichever comes first
- Delete indices once they are older than `3d`

Related config references:

- [filebeat/filebeat.yml](filebeat/filebeat.yml): `setup.ilm.policy_file: "/usr/share/filebeat/filebeat-ilm.json"`
- [metricbeat/metricbeat.yml](metricbeat/metricbeat.yml): `setup.ilm.policy_file: "/usr/share/metricbeat/metricbeat-ilm.json"`

## Running the Stacks

### HTPC stack script behavior

[runHTPCStack.sh](runHTPCStack.sh):

- With yes: runs docker compose up -d --build
- Without yes: runs docker compose config and writes merged output to HTPCconfig.yml

### Observer stack script behavior

[runObserverStack.sh](runObserverStack.sh):

- With yes: runs docker-compose up -d --build
- Without yes: runs docker-compose config and writes merged output to HTPCconfig.yml

Note: the observer script currently writes config output to HTPCconfig.yml as well.

## Service Reference

### Core media pipeline

- SABnzbd: Usenet downloader
- Transmission: torrent downloader
- Prowlarr: indexer manager
- Radarr: movies
- Sonarr: TV series
- Readarr: ebooks/audiobooks
- Mylar3: comics

### Media servers and analytics

- Plex
- Jellyfin
- Emby
- Tautulli (Plex activity analytics)

### Utility and anti-bot support

- FlareSolverr for Cloudflare/challenge handling in supported workflows
- Overseerr for media request management (movies and TV via Plex/Jellyfin integration)

## Observability Notes

- Elasticsearch and Kibana images in [observabilityServices.yml](observabilityServices.yml) are ARM64-tagged.
- If your observer host is not ARM64, use compatible image tags.
- Portainer is configured to connect to a Docker TCP endpoint based on BEATS_HOST.
- Ensure Docker remote API exposure is intentional and secured.

## Troubleshooting

### Compose validation first

Run config-only mode to catch variable and syntax errors:

```bash
./runHTPCStack.sh
./runObserverStack.sh
```

### Permission problems

- Verify PUID/PGID values match the host user owning your bind mounts.
- Ensure media/download directories are writable by containers.

### Beats not ingesting data

- Confirm Elasticsearch host in Beats config is reachable.
- Confirm Docker socket and /var/lib/docker mounts are present.
- Check container logs:

```bash
docker logs filebeat
docker logs metricbeat
```

### Beats config file ownership error

If `filebeat` or `metricbeat` exits immediately and you see an error such as:

```text
Exiting: error loading config file: config file ("filebeat.yml") must be owned by the user identifier (uid=0) or root
```

Docker Compose mounts the config files from the host filesystem. Beats requires these files to be owned by root with no group/other write permissions.

Fix (run from the root of the repo on the HTPC host):

```bash
sudo chown root:root filebeat/filebeat.yml
sudo chown root:root metricbeat/metricbeat.yml
sudo chmod go-w filebeat/filebeat.yml
sudo chmod go-w metricbeat/metricbeat.yml
docker restart filebeat metricbeat
```

This is a one-time step after initial setup, or after any pull that modifies those files. See step 6 of [Quick Start](#quick-start).

### Network and static IP issues

- The HTPC stack uses static IP assignments in 172.66.0.0/16.
- Ensure no overlap with existing Docker or LAN subnets.

## Security and Public Repo Guidance

- Do not commit secrets, API keys, tokens, or private hostnames.
- Prefer publishing sanitized env examples (for example, *.env.example) instead of private values.
- Restrict exposed ports to trusted networks.
- Use VPN/reverse proxy authentication for remote access.

## Contributing

Contributions are welcome.

Please review [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

This project follows [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

### How to contribute

1. Fork the repository.
2. Create a feature branch.
3. Make focused changes with clear commit messages.
4. Validate with compose config checks.
5. Open a pull request with:
    - What changed
    - Why it changed
    - Any migration steps

### Recommended contribution areas

- Improve portability of absolute host paths
- Unify docker compose vs docker-compose usage
- Add cross-platform scripts (PowerShell + Bash)
- Add healthchecks and startup dependencies where appropriate

## Roadmap Ideas

- Replace hardcoded IPs in Beats configs with env-driven values
- Add profiles to split optional services
- Add reverse proxy integration examples
- Add backup/restore guide for config volumes
- Publish architecture diagrams

## License

This project is licensed under the MIT License.

See [LICENSE](LICENSE) for the full text.

## Security

For vulnerability reporting and security guidance, see [SECURITY.md](SECURITY.md).
