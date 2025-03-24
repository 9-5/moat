<p align="center"><img src="assets\moat.png" height="250" width="250"/></p>

# Moat - Build a moat around your self-hosted apps.

Moat is a lightweight, FastAPI-based security gateway that provides authentication and reverse proxying capabilities for your web services. It can manage service discovery through Docker labels or static configuration.

## Table of Contents

[Screenshots](#screenshots)

[Features](#features)

[Prerequisites](#prerequisites)

[Installation](#installation)

[Configuration](#configuration)

[Running Moat](#running-moat)

[Usage](#usage)

[CLI Commands](#cli-commands)

[Troubleshooting](#troubleshooting)

## Screenshots
<div align="center">
<img src="https://github.com/user-attachments/assets/917da6b1-d226-40cb-9f44-4d0d-8369-567c29b793e2/moat_screenshot_login.png" width="350">
<img src="https://github.com/user-attachments/assets/917da6b1-d226-40cb-9f44-4d0d-8369-567c29b793e2/moat_screenshot_admin.png" width="350">
</div>

## Features

*   **Authentication:** Secure your services with username/password authentication.
*   **Reverse Proxy:** Route traffic to your internal services based on hostname.
*   **Docker Integration:** Automatically discover and proxy Docker containers.
*   **Centralized Management:** Configure services and authentication in one place.
*   **Admin UI:** Easy configuration and management via a web interface.

## Prerequisites

*   Python 3.7+
*   Docker (optional, for Docker-based service discovery)

## Installation

```bash
pip install fastapi uvicorn python-dotenv
```

## Configuration

Moat requires a `config.yml` file in the working directory. You can generate a default configuration using the `init-config` command:

```bash
moat init-config
```

Edit the `config.yml` file to configure Moat's settings, including the `secret_key`, `database_url`, and service definitions.

Example `config.yml`:

```yaml
listen_host: 0.0.0.0
listen_port: 8000
secret_key: YOUR_VERY_SECRET_KEY_CHANGE_THIS_NOW_PLEASE
access_token_expire_minutes: 60
database_url: sqlite+aiosqlite:///./moat.db
moat_base_url: https://moat.bor.i.ng # MUST be the public URL of Moat itself.
cookie_domain: .bor.i.ng

docker_monitor_enabled: true
moat_label_prefix: moat

static_services:
  - hostname: app.bor.i.ng
    target_url: http://127.0.0.1:9090
```

## Running Moat

```bash
uvicorn main:app --reload
```

Or, using the Moat CLI:

```bash
moat run --reload
```

## Usage

Once Moat is running, access it in your browser. You will be prompted to log in. After logging in, Moat will proxy requests to your configured services based on the hostname.

## CLI Commands

*   `run`: Starts the Moat server.
    *   `--reload`: Enables auto-reloading for development.
*   `init-config`: Creates a default `config.yml` file.
*   `add-static-service`: Adds a static service to the configuration.
*   `bind-static-service`: Binds a static service to a Docker container's hostname and port.

## Troubleshooting

* **"Secret key not configured" / "Moat configuration file not found"**: Ensure `config.yml` exists in the working directory and `secret_key` is set. Run `moat init-config`.
* **Redirect loops or incorrect login URL**: Double-check `moat_base_url` in `config.yml`. It must be the public URL of Moat itself.
* **Cookies not working across subdomains**: Verify `cookie_domain` is set correctly (e.g., `.yourdomain.com`).
* **Docker services not appearing**:
   * Ensure `docker_monitor_enabled: true`.
   * Check Moat's logs for Docker connection errors.
   * Verify container labels match `moat_label_prefix` and include `enable`, `hostname`, and `port`.
   * Ensure Moat has access to the Docker socket (`/var/run/docker.sock`).