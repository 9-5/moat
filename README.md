<p align="center"><img src="assets\moat.png" height="250" width="250"/></p>

# Moat - Build a moat around your self-hosted apps.

Moat is a lightweight, FastAPI-based security gateway that provides authentication and reverse proxying capabilities for your web services. It can manage service discovery through Docker labels or static configuration.

## Table of Contents

[Screenshots](#screenshots)

[Features](#features)

[Prerequisites](#prerequisites]

[Installation](#installation)

[Configuration](#configuration)

[Running Moat](#running-moat)

[Usage](#usage)

[CLI Commands](#cli-commands)

[Troubleshooting](#troubleshooting)

## Screenshots
<div align="center">
<img src="https://github.com/user-attachments/assets/917da6b1-d226-40cb-9f44-9418-67651221e656/moat_login.png" width="400" height="250">
<img src="https://github.com/user-attachments/assets/917da6b1-d226-40cb-9f44-67651221e656/moat_protected.png" width="400" height="250">
</div>

## Features

*   **Authentication**: Secure your applications with username/password authentication.
*   **Reverse Proxy**: Route traffic to your applications based on hostname.
*   **Service Discovery**: Automatically discover services via Docker labels.
*   **Single Sign-On (SSO)**: Authenticate once and access multiple applications.
*   **Centralized Configuration**: Manage all your services from a single `config.yml` file.
*   **Admin UI**: Web interface to manage configuration.
*   **Cloudflare Tunnel Support**: Route traffic through Cloudflare's edge network.

## Prerequisites

*   Python 3.9+
*   Docker (optional, for service discovery)

## Installation

```bash
git clone https://github.com/your-username/moat.git
cd moat
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

## Configuration

Moat is configured via a `config.yml` file. An example configuration is provided in `config.example.yml`. You can initialize a new configuration file with:

```bash
moat init-config
```

Key configuration options:

*   `listen_host`: The host Moat listens on (default: `0.0.0.0`).
*   `listen_port`: The port Moat listens on (default: `8000`).
*   `secret_key`: A secret key used to sign access tokens. Generate a strong key using `openssl rand -hex 32`.
*   `database_url`: The URL of the SQLite database (default: `sqlite+aiosqlite:///./moat.db`).
*   `moat_base_url`: The public URL of Moat itself (e.g., `https://moat.yourdomain.com`). This is crucial if Moat is behind a reverse proxy or tunnel.
*   `cookie_domain`: The domain for the SSO cookie (e.g., `.yourdomain.com`).

## Running Moat

```bash
moat run
```

## Usage

Once Moat is running, access the admin UI at `http://<moat_host>:<moat_port>/moat/admin/config` to configure your services.

You'll need to create a user first using the `moat create-user` CLI command.

Moat will then reverse proxy requests to your applications based on the hostname.

## CLI Commands

*   `moat run`: Starts the Moat server.
*   `moat init-config`: Creates a default `config.yml` file.
*   `moat create-user`: Creates a new user in the database.
*   `moat add-static-service`: Adds a static service to the configuration.
*   `moat docker:bind`: Adds a static service bound to a Docker container's hostname and port.

## Troubleshooting

*   **"Secret key not configured" / "Moat configuration file not found"**: Ensure `config.yml` exists in the working directory and `secret_key` is set. Run `moat init-config`.
*   **Redirect loops or incorrect login URL**: Double-check `moat_base_url` in `config.yml`. It must be the public URL of Moat itself.
*   **Cookies not working across subdomains**: Verify `cookie_domain` is set correctly (e.g., `.yourdomain.com`).
*   **Docker services not appearing**:
   * Ensure `docker_monitor_enabled: true`.
   * Check Moat's logs for Docker connection errors.
   * Verify container labels match `moat_label_prefix` and include `enable`, `hostname`, and `port`.
   * Ensure Moat has access to the Docker socket (`/var/run/docker.sock`).