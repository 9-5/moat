<p align="center"><img src="assets\moat.png" height="250" width="250"/></p>

# Moat - Build a moat around your self-hosted apps.

Moat is a lightweight, FastAPI-based security gateway that provides authentication and reverse proxying capabilities for your web services. It can manage service discovery through Docker labels or static configuration.

## Table of Contents

[Screenshots](#screenshots)

[Features](#features)

[Prerequisites](#prerequisites)

[Installation](#installation)

[Configuration](#configuration)

[Running Moat](#running-Moat)

[Usage](#usage)

[CLI Commands](#cli-commands)

[Troubleshooting](#troubleshooting)

## Screenshots
<div align="center">
<img src="https://github.com/user-attachments/assets/917da6b1-d226-40cb-9f44-a979-824f3a6ef68d/moat-admin-config.png" width="800" height="450">
</div>
<br>
<div align="center">
<img src="https://github.com/user-attachments/assets/917da6b1-d226-40cb-9f44-a979-824f3a6ef68d/moat-login.png" width="800" height="450">
</div>

## Features

*   **Authentication**: User login and session management.
*   **Reverse Proxy**: Securely proxies requests to backend services.
*   **Service Discovery**: Automatically discovers services via Docker labels.
*   **Static Configuration**: Supports manually configured services.
*   **Admin UI**: Web interface for configuration and management.
*   **Centralized Security**: Enforces authentication before accessing any proxied service.

## Prerequisites

*   Docker (if using Docker service discovery)
*   Python 3.7+

## Installation

```bash
git clone https://github.com/your-username/moat.git
cd moat
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Configuration

1.  **Create Configuration File**:
    *   Run `moat init-config` to create `config.yml` in the working directory.
    *   Alternatively, copy `config.example.yml` to `config.yml`.
2.  **Edit `config.yml`**:
    *   Set `secret_key` (generate a strong key using `openssl rand -hex 32`).
    *   Configure `moat_base_url` to the public URL where Moat is accessible.
    *   Adjust `cookie_domain` for proper cookie handling across subdomains (e.g., `.yourdomain.com`).
    *   If using Docker, ensure `docker_monitor_enabled: true` and configure `moat_label_prefix`.
    *   Define `static_services` for non-Docker applications.

Example `config.yml`:

```yaml
listen_host: 0.0.0.0
listen_port: 8000
secret_key: "YOUR_VERY_SECRET_KEY_CHANGE_THIS_NOW_PLEASE"
access_token_expire_minutes: 60
database_url: sqlite+aiosqlite:///./moat.db
moat_base_url: https://moat.yourdomain.com
cookie_domain: .yourdomain.com
docker_monitor_enabled: true
moat_label_prefix: moat
static_services:
  - hostname: app1.yourdomain.com
    target_url: http://localhost:3000
```

## Running Moat

```bash
python -m moat.main run
```

## Usage

1.  **Access Moat**: Open your browser to the `moat_base_url` you configured.
2.  **Login**: Log in with your username and password.
3.  **Access Services**: Moat will proxy requests to your configured services, enforcing authentication.

### Docker Service Discovery

Moat automatically discovers services based on Docker labels. Ensure your containers have the following labels:

*   `moat.enable=true`: Enables Moat proxying for this container.
*   `moat.hostname=app.yourdomain.com`: The public hostname for the service.
*   `moat.port=80`: The port the service is listening on inside the container.

Example `docker-compose.yml`:

```yaml
version: "3.8"
services:
  my-app:
    image: your-app-image
    labels:
      moat.enable: "true"
      moat.hostname: "app.yourdomain.com"
      moat.port: "80"
    ports:
      - "3000:80"
```

### Static Services

For services not running in Docker, define them in the `static_services` section of `config.yml`.

```yaml
static_services:
  - hostname: "service1.yourdomain.com"
    target_url: "http://127.0.0.1:9001"
```

## CLI Commands

*   `moat init-config`: Creates a default `config.yml` file.
*   `moat create-user <username>`: Creates a new user.
*   `moat run`: Starts the Moat server.
*   `moat add-static-service <public_hostname> <target_url>`: Adds a static service to the config.

## Troubleshooting

* **"Secret key not configured" / "Moat configuration file not found"**: Ensure `config.yml` exists in the working directory and `secret_key` is set. Run `moat init-config`.
* **Redirect loops or incorrect login URL**: Double-check `moat_base_url` in `config.yml`. It must be the public URL of Moat itself.
* **Cookies not working across subdomains**: Verify `cookie_domain` is set correctly (e.g., `.yourdomain.com`).
* **Docker services not appearing**:
   * Ensure `docker_monitor_enabled: true`.
   * Check Moat's logs for Docker connection errors.
   * Verify container labels match `moat_label_prefix` and include `enable`, `hostname`, and `port`.
   * Ensure Moat has access to the Docker socket (`/var/run/docker.sock`).