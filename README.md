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
<img src="https://github.com/user-attachments/assets/917da6b1-d226-40cb-9f44-e77d-40f2-9cc3-d52479833a6d/moat-admin-ui.png" height="400" width="600"/>
</div>
<br>
<div align="center">
<img src="https://github.com/user-attachments/assets/44b3c059-bca9-456c-b25f-dd02293d4a94/moat-login-page.png" height="400" width="600"/>
</div>

## Features

*   **Authentication**: Secure your applications with username/password authentication.
*   **Reverse Proxy**: Route traffic to your applications based on hostname.
*   **Docker Integration**: Automatically discover and proxy Docker containers using labels.
*   **Static Configuration**: Define services manually for non-Docker applications.
*   **Single Sign-On (SSO)**: Authenticate once and access multiple applications seamlessly.
*   **Admin UI**: Configure Moat through a web-based interface.

## Prerequisites

*   Python 3.7+
*   Docker (optional, for Docker integration)

## Installation

```bash
git clone https://github.com/your-username/moat.git
cd moat
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Moat uses a `config.yml` file for configuration. You can create it manually or use the `moat init-config` command.

```bash
cp config.example.yml config.yml
# OR
moat init-config
```

Edit `config.yml` to set your desired settings:

```yaml
listen_host: "0.0.0.0"
listen_port: 8000
secret_key: "YOUR_VERY_SECRET_KEY_CHANGE_THIS_NOW_PLEASE" # Generate with: openssl rand -hex 32
access_token_expire_minutes: 60
database_url: "sqlite+aiosqlite:///./moat.db"
moat_base_url: null
cookie_domain: null
docker_monitor_enabled: true
moat_label_prefix: "moat"
static_services:
  - hostname: "service1.localhost"
    target_url: "http://127.0.0.1:9001"
  - hostname: "another.example.com"
    target_url: "http://192.168.1.100:8080"
```

## Running Moat

```bash
moat run
```

## Usage

Once Moat is running, access it through your configured `moat_base_url`. You will be prompted to log in. After logging in, you can access your proxied applications through their configured hostnames.

## CLI Commands

*   `moat run`: Starts the Moat server.
*   `moat init-config`: Generates a default `config.yml` file.
*   `moat add-user`: Creates a new user in the database.
*   `moat add-static`: Adds a static service to the configuration.
*   `moat docker:bind`: Adds a static service bound to a Docker container.

## Troubleshooting

* **"Secret key not configured" / "Moat configuration file not found"**: Ensure `config.yml` exists in the working directory and `secret_key` is set. Run `moat init-config`.
* **Redirect loops or incorrect login URL**: Double-check `moat_base_url` in `config.yml`. It must be the public URL of Moat itself.
* **Cookies not working across subdomains**: Verify `cookie_domain` is set correctly (e.g., `.yourdomain.com`).
* **Docker services not appearing**:
   * Ensure `docker_monitor_enabled: true`.
   * Check Moat's logs for Docker connection errors.
   * Verify container labels match `moat_label_prefix` and include `enable`, `hostname`, and `port`.
   * Ensure Moat has access to the Docker socket (`/var/run/docker.sock`).