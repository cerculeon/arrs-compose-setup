# HTPC Config

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
- FlareSolverr
- Filebeat
- Metricbeat

The observability stack in [observabilityServices.yml](observabilityServices.yml) includes:

- Elasticsearch
- Kibana
- Portainer

## Repository Layout

```
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
3. Validate configuration (without starting containers):

```bash
./runHTPCStack.sh
./runObserverStack.sh
```

4. Start stacks:

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

### Observer Env Variables

Defined in [OBSERVER/OBSERVER_envValues.env](OBSERVER/OBSERVER_envValues.env):

- CONFIG_ROOT
- KIBANA_HOST_IP
- BEATS_HOST

### Beats Config

- Filebeat config: [filebeat/filebeat.yml](filebeat/filebeat.yml)
- Metricbeat config: [metricbeat/metricbeat.yml](metricbeat/metricbeat.yml)
- Metricbeat Docker module: [metricbeat/modules.d/docker.yml](metricbeat/modules.d/docker.yml)

Important:

- The HTPC compose file currently mounts Beats config from an absolute path under /home/mark/htpc-config.
- For portability, update these paths/IPs for your environment.

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
- Add env example templates
- Add healthchecks and startup dependencies where appropriate
- Add CI checks for compose validation and linting

## Roadmap Ideas

- Replace hardcoded IPs in Beats configs with env-driven values
- Add profiles to split optional services
- Add reverse proxy integration examples
- Add backup/restore guide for config volumes
- Publish architecture diagrams

## License

This project is licensed under the MIT License.

See [LICENSE](LICENSE) for the full text.
