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
<img src="https://github.com/user-attachments/assets/917da6b1-d226-40cb-9f44-4d47-a70e-2fd37699d75c/moat-login.png" width="400">
<img src="https://github.com/user-attachments/assets/917da6b1-d226-40cb-9f44-4d47-a70e-2fd37699d75c/moat-admin.png" width="400">
</div>

## Features

*   **Authentication**: User login and session management.
*   **Reverse Proxy**: Securely proxies requests to backend services.
*   **Service Discovery**: Automatically discovers services via Docker labels.
*   **Static Configuration**: Define services manually in the configuration file.
*   **Single Sign-On (SSO)**: Users only need to log in once to access multiple services.
*   **Admin UI**: Web interface for managing configuration.

## Prerequisites

*   Python 3.7+
*   Docker (if using Docker-based service discovery)

## Installation

```bash
pip install fastapi uvicorn python-dotenv aiosqlite pyyaml docker python-jose passlib aiohttp
```

## Configuration

Moat is configured via a `config.yml` file. You can create a default configuration using the CLI:

```bash
moat init-config
```

Edit the `config.yml` file to set your desired settings:

*   `listen_host`: The host Moat listens on (e.g., `0.0.0.0` for all interfaces).
*   `listen_port`: The port Moat listens on (e.g., `8000`).
*   `secret_key`: A random, securely generated secret key used for signing JWTs.  **IMPORTANT: Change this!**
*   `access_token_expire_minutes`:  How long access tokens are valid.
*   `database_url`:  URL for the aiosqlite database (e.g., `sqlite+aiosqlite:///./moat.db`).
*   `moat_base_url`: The public URL of Moat itself (e.g., `https://moat.example.com`). Required if Moat is behind a reverse proxy.
*   `cookie_domain`: The domain for cookies (e.g., `.example.com` for all subdomains).  Set to `null` to disable cookies.
*   `docker_monitor_enabled`: Whether to automatically discover services via Docker labels.
*   `moat_label_prefix`: The prefix for Docker labels (e.g., `moat.`).
*   `static_services`: A list of manually configured services.

Example `config.yml`:

```yaml
listen_host: 0.0.0.0
listen_port: 8000
secret_key: YOUR_VERY_SECRET_KEY_CHANGE_THIS_NOW_PLEASE
access_token_expire_minutes: 60
database_url: sqlite+aiosqlite:///./moat.db
moat_base_url: https://moat.example.com
cookie_domain: .example.com
docker_monitor_enabled: true
moat_label_prefix: moat
static_services:
  - hostname: app1.example.com
    target_url: http://127.0.0.1:9001
```

## Running Moat

```bash
python -m moat.main run
```

## Usage

Once Moat is running, access it via your configured `moat_base_url`. You'll be prompted to log in. After logging in, you can access your proxied applications via their configured hostnames.

## CLI Commands

*   `moat init-config`: Creates a default `config.yml` file.
*   `moat add-static-service`: Adds a static service to the `config.yml` file.
*   `moat remove-static-service`: Removes a static service from the `config.yml` file.
*   `moat run`: Starts the Moat server.
*   `moat create-user`: Creates a new user in the database.
*   `moat bind`: Automatically creates static service entry from a docker container.

## Troubleshooting

* **"Secret key not configured" / "Moat configuration file not found"**: Ensure `config.yml` exists in the working directory and `secret_key` is set. Run `moat init-config`.
* **Redirect loops or incorrect login URL**: Double-check `moat_base_url` in `config.yml`. It must be the public URL of Moat itself.
* **Cookies not working across subdomains**: Verify `cookie_domain` is set correctly (e.g., `.yourdomain.com`).
* **Docker services not appearing**:
   * Ensure `docker_monitor_enabled: true`.
   * Check Moat's logs for Docker connection errors.
   * Verify container labels match `moat_label_prefix` and include `enable`, `hostname`, and `port`.
   * Ensure Moat has access to the Docker socket (`/var/run/docker.sock`).