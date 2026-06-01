# Secrets Management

Kubernetes Secrets are **never committed to this repository**.

This directory documents how to create and manage secrets for this stack.
For local development / first-time setup the secrets can be created manually with
`kubectl`. In CI/CD they are created automatically by the deploy workflow using
values stored as **GitHub Secrets**.

---

## Required Secrets

### `cloudflared-tunnel-token` (namespace: `htpc`)

Contains the Cloudflare Tunnel token obtained from the
[Zero Trust dashboard](https://one.dash.cloudflare.com/) under
**Networks → Tunnels → Create a tunnel**.

**GitHub Secret name:** `CLOUDFLARED_TUNNEL_TOKEN`

**Create manually:**

```bash
kubectl create secret generic cloudflared-tunnel-token \
  --namespace htpc \
  --from-literal=token=<YOUR_TUNNEL_TOKEN>
```

**Update:**

```bash
kubectl create secret generic cloudflared-tunnel-token \
  --namespace htpc \
  --from-literal=token=<YOUR_TUNNEL_TOKEN> \
  --dry-run=client -o yaml | kubectl apply -f -
```

---

## GitHub Secrets Required by CI

| Secret Name            | Used For                                              |
|------------------------|-------------------------------------------------------|
| `KUBECONFIG_B64`       | Base64-encoded kubeconfig to authenticate to MicroK8s |
| `CLOUDFLARED_TUNNEL_TOKEN` | Cloudflare Tunnel token injected into the cluster |

### Generating `KUBECONFIG_B64`

On your MicroK8s node, run:

```bash
microk8s config | base64 -w 0
```

Copy the output and store it as the `KUBECONFIG_B64` GitHub Secret.

If using a **self-hosted GitHub Actions runner** on the MicroK8s node,
`KUBECONFIG_B64` is optional — the runner can use MicroK8s directly:

```bash
microk8s kubectl ...
# or add the runner user to the microk8s group:
sudo usermod -aG microk8s <runner-user>
```

---

## Template Files

`k8s/base/networking/cloudflared/secret-template.yaml` contains a **template**
with a placeholder value. It is excluded from the Kustomize build and is
provided only as a reference for the secret structure.

---

## Security Notes

- Real token values must **never** be committed to this repository.
- If a token is accidentally committed, rotate it immediately in the Cloudflare
  Zero Trust dashboard and update the GitHub Secret.
- Consider using [Sealed Secrets](https://github.com/bitnami-labs/sealed-secrets)
  or [External Secrets Operator](https://external-secrets.io) if you want to
  store encrypted secret manifests in the repository.
