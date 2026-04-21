# Deployment recipes

Choose the guide that matches your infrastructure:

| Recipe | Use case |
|---|---|
| [Docker Compose](./docker-compose.md) | Single host, staging, self-hosted teams |
| [Kubernetes](./kubernetes.md) | Managed cluster using plain manifests |
| [Helm](./helm.md) | Multi-environment installs with values-driven config |
| [Bare-metal / systemd](./bare-metal.md) | Air-gapped hosts, no container runtime |

All four recipes cover: prerequisites, environment config, first run,
upgrade, and backup.

## Which recipe should I choose?

- **Just getting started?** Use Docker Compose — one command brings up all
  services.
- **Already running Kubernetes?** Use the Kubernetes manifests or Helm chart
  (Helm is easier to maintain across environments).
- **Air-gapped or resource-constrained host?** Use the bare-metal / systemd
  recipe.

## Shared config reference

Environment variables and secret generation are documented in
[../configuration.md](../configuration.md).
