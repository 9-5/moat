<p align="center"><img src="assets\moat.png" height="250" width="250"/></p>

# Moat - Build a moat around your self-hosted apps.

Moat is a lightweight, FastAPI-based security gateway that provides authentication and reverse proxying capabilities for your web services. It can manage service discovery through Docker labels or static configuration.

## Table of Contents

[Screenshots](#screenshots)

[Features](#features)

[Prerequisites](#prerequisites)

[Installation](#installation)

[Configuration](#configuration)

[Running Moat](#running_moat)

[Usage](#usage)

[CLI Commands](#cli-commands)

[Troubleshooting](#troubleshooting)

## Screenshots
<div align="center">
<img src="https://github.com/user-attachments/assets/917da6b1-d226-40cb-9f44-b114-44c2-a004-c5c18974f127/moat-screenshot.png" width="800"/>
</div>

## Features

*   **Authentication:** Secure your applications with username/password authentication.
*   **Reverse Proxy:** Route traffic to your applications based on hostname.
*   **Single Sign-On (SSO):** Users only need to log in once to access multiple applications.
*   **Docker Integration:** Automatically discover and proxy Docker containers using labels.
*   **Static Configuration:** Define static routes for non-Docker applications.
*   **Admin UI:** Web interface for configuration and user management.
*   **Observability:** Health check endpoint and logging.

## Prerequisites

*   Python 3.9+
*   Docker (optional, for Docker-based service discovery)

## Installation

```bash
pip install "moat[all]"
```

## Configuration

Moat uses a `config.yml` file for configuration. You can generate a default configuration file using the `moat init-config` CLI command.

```bash
moat init-config
```

Edit the `config.yml` file to configure Moat to your needs. The most important settings are:

*   `secret_key`: A secret key used to sign access tokens. **Change this to a strong, randomly generated value!**
*   `moat_base_url`: The public URL of your Moat instance. This is used for redirects and cookie settings.
*   `cookie_domain`: The domain for which the Moat cookie should be valid. This is used for SSO.
*   `docker_monitor_enabled`: Whether to automatically discover and proxy Docker containers using labels.
*   `moat_label_prefix`: The prefix for Docker labels used to configure Moat.

Here's an example `config.yml`:

```yaml
listen_host: 0.0.0.0
listen_port: 8000
secret_key: YOUR_VERY_SECRET_KEY_CHANGE_THIS_NOW_PLEASE
access_token_expire_minutes: 60
database_url: sqlite+aiosqlite:///./moat.db
moat_base_url: https://moat.bor.i.ng
cookie_domain: .bor.i.ng
docker_monitor_enabled: true
moat_label_prefix: moat
static_services:
- hostname: app.bor.i.ng
  target_url: http://127.0.0.1:9090
```

## Running Moat

Start the Moat server using the `moat run` CLI command.

```bash
moat run
```

## Usage

Once Moat is running, you can access your applications through the Moat reverse proxy. You will be prompted to log in before accessing any protected application.

## CLI Commands

Moat provides a few CLI commands to help you manage your Moat instance.

*   `moat init-config`: Generates a default `config.yml` file.
*   `moat run`: Starts the Moat server.
*   `moat create-user`: Creates a new user in the database.
*   `moat add`: Adds a static service to the configuration.

## Troubleshooting

* **"Secret key not configured" / "Moat configuration file not found"**: Ensure `config.yml` exists in the working directory and `secret_key` is set. Run `moat init-config`.
* **Redirect loops or incorrect login URL**: Double-check `moat_base_url` in `config.yml`. It must be the public URL of Moat itself.
* **Cookies not working across subdomains**: Verify `cookie_domain` is set correctly (e.g., `.yourdomain.com`).
* **Docker services not appearing**:
   * Ensure `docker_monitor_enabled: true`.
   * Check Moat's logs for Docker connection errors.
   * Verify container labels match `moat_label_prefix` and include `enable`, `hostname`, and `port`.
   * Ensure Moat has access to the Docker socket (`/var/run/docker.sock`).