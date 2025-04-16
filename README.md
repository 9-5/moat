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
<img src="https://github.com/user-attachments/assets/917da6b1-d226-40cb-9f44-a647-c7a5ae19a1f5/moat-admin-ui.png" width="700" height="350">
</div>

## Features

*   **Authentication**: User authentication with username/password and secure cookie-based sessions.
*   **Reverse Proxy**: Routes traffic to backend services based on hostname.
*   **Service Discovery**: Automatically discovers services via Docker labels or manual static configuration.
*   **Single Sign-On (SSO)**: Provides a central login for all your self-hosted applications.
*   **Admin UI**: Web interface for configuration management.
*   **CLI**: Command-line interface for initialization and advanced tasks.
*   **HTTPS Support**: Secure communication with automatic or manual TLS certificate configuration.

## Prerequisites

*   [Docker](https://www.docker.com/) (optional, for Docker-based service discovery)
*   [Python 3.7+](https://www.python.org/)
*   [pip](https://pypi.org/project/pip/)

## Installation

```bash
git clone https://github.com/jordanrobinson/moat.git
cd moat
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Configuration

1.  **Initialize Configuration**:

    ```bash
    moat init-config
    ```

    This creates a `config.yml` file in your working directory.

2.  **Edit `config.yml`**:

    *   Set a strong `secret_key`. Generate one using `openssl rand -hex 32`.
    *   Configure `moat_base_url` to the public URL of your Moat instance.
    *   Adjust `cookie_domain` to match your application's domain (e.g., `.yourdomain.com`).
    *   Define static services or enable Docker monitoring.

    Example `config.yml`:

    ```yaml
    listen_host: "0.0.0.0"
    listen_port: 8000
    secret_key: "YOUR_VERY_SECRET_KEY_CHANGE_THIS_NOW_PLEASE"
    access_token_expire_minutes: 60
    database_url: "sqlite+aiosqlite:///./moat.db"
    moat_base_url: "https://moat.yourdomain.com"
    cookie_domain: ".yourdomain.com"
    docker_monitor_enabled: true
    moat_label_prefix: "moat"
    static_services:
      - hostname: "service1.yourdomain.com"
        target_url: "http://127.0.0.1:9001"
    ```

## Running Moat

```bash
moat run
```

This starts the Moat server.  Access the admin UI at `https://moat.yourdomain.com/moat/admin/config` (adjust URL as needed).

## Usage

1.  **Configure Services**:

    *   **Docker**: Add labels to your Docker containers.  For example:

        ```yaml
        labels:
          moat.enable: "true"
          moat.hostname: "app1.yourdomain.com"
          moat.port: "80"
        ```

    *   **Static**: Define services directly in `config.yml`.

2.  **Access Services**:  Once configured, your services are accessible via their hostnames (e.g., `https://app1.yourdomain.com`).  Moat will redirect unauthenticated users to the login page.

## CLI Commands

*   `moat init-config`: Creates a default `config.yml` file.
*   `moat run`: Starts the Moat server.
*   `moat create-user`: Creates a new user.  Example: `moat create-user --username admin`.  You will be prompted for a password.
*   `moat docker:bind`: Binds a static service to a Docker container. Example: `moat docker:bind --hostname app.example.com <container_name_or_id>`.  This automatically configures a static service entry pointing to the container.

## Troubleshooting

* **"Secret key not configured" / "Moat configuration file not found"**: Ensure `config.yml` exists in the working directory and `secret_key` is set. Run `moat init-config`.
* **Redirect loops or incorrect login URL**: Double-check `moat_base_url` in `config.yml`. It must be the public URL of Moat itself.
* **Cookies not working across subdomains**: Verify `cookie_domain` is set correctly (e.g., `.yourdomain.com`).
* **Docker services not appearing**:
   * Ensure `docker_monitor_enabled: true`.
   * Check Moat's logs for Docker connection errors.
   * Verify container labels match `moat_label_prefix` and include `enable`, `hostname`, and `port`.
   * Ensure Moat has access to the Docker socket (`/var/run/docker.sock`).