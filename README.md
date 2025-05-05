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
<img src="https://github.com/user-attachments/assets/917da6b1-d226-40cb-9f44-b1ba-41a5-850b-732e394e0910/moat-login.png" width="400">
<img src="https://github.com/user-attachments/assets/917da6b1-d226-40cb-9f44-b1ba-41a5-850b-732e394e0910/moat-admin.png" width="400">
</div>

## Features

- **Authentication**: User authentication with username/password.
- **Authorization**: Access control based on user roles (planned).
- **Reverse Proxy**: Proxies requests to backend services after successful authentication.
- **Service Discovery**: Automatic service discovery using Docker labels.
- **Static Configuration**: Define services manually in the configuration file.
- **Centralized Management**: Web-based admin UI for configuration and monitoring.
- **Single Sign-On (SSO)**: Authenticate once and access multiple services without re-logging.
- **Session Management**: Secure cookie-based session management.
- **HTTPS Support**: Enforce HTTPS for secure communication.
- **Rate Limiting**: Protect backend services from abuse (planned).

## Prerequisites

*   Python 3.7+
*   Docker (optional, for service discovery)

## Installation

```bash
git clone https://github.com/your-username/moat.git
cd moat
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Moat uses a `config.yml` file for configuration. You can initialize a default configuration file using the CLI:

```bash
moat init-config
```

Edit the `config.yml` file to set your desired settings.  The most important is `secret_key`, which you should generate with `openssl rand -hex 32`.

Example `config.yml`:

```yaml
listen_host: 0.0.0.0
listen_port: 8000
secret_key: "YOUR_VERY_SECRET_KEY_CHANGE_THIS_NOW_PLEASE" # Generate with: openssl rand -hex 32
access_token_expire_minutes: 60
database_url: sqlite+aiosqlite:///./moat.db
moat_base_url: https://moat.yourdomain.com
cookie_domain: .yourdomain.com
docker_monitor_enabled: true
moat_label_prefix: moat
static_services:
  - hostname: app.yourdomain.com
    target_url: http://127.0.0.1:9090
```

## Running Moat

```bash
moat run
```

## Usage

Once Moat is running, access the admin UI at `https://moat.yourdomain.com/moat/admin` to configure services and manage users.

To protect a service, configure it either as a static service or using Docker labels.  For Docker, the labels should look like:

```yaml
labels:
  moat.enable: "true"
  moat.hostname: "myservice.yourdomain.com"
  moat.port: "80"
```

Make sure `docker_monitor_enabled` is set to `true` in `config.yml`.

## CLI Commands

*   `moat init-config`: Initializes a default `config.yml` file.
*   `moat run`: Starts the Moat server.
*   `moat add-static-service <hostname> <target_url>`: Adds a static service to the configuration.
*   `moat update-static-service <hostname> <target_url>`: Updates an existing static service's target URL.
*   `moat bind-static-service <hostname> <container_name>`: Automatically configures a static service based on a running Docker container's port.

## Troubleshooting

* **"Secret key not configured" / "Moat configuration file not found"**: Ensure `config.yml` exists in the working directory and `secret_key` is set. Run `moat init-config`.
* **Redirect loops or incorrect login URL**: Double-check `moat_base_url` in `config.yml`. It must be the public URL of Moat itself.
* **Cookies not working across subdomains**: Verify `cookie_domain` is set correctly (e.g., `.yourdomain.com`).
* **Docker services not appearing**:
   * Ensure `docker_monitor_enabled: true`.
   * Check Moat's logs for Docker connection errors.
   * Verify container labels match `moat_label_prefix` and include `enable`, `hostname`, and `port`.
   * Ensure Moat has access to the Docker socket (`/var/run/docker.sock`).