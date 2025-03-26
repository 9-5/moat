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
<img src="https://github.com/user-attachments/assets/917da6b1-d226-40cb-9f44-a4f9-ca3a2f9bb188/moat-login.png" height="300" width="600"/>
<img src="https://github.com/user-attachments/assets/a00a79fb-8832-404f-a958-176965f225a3/moat-admin.png" height="300" width="600"/>
</div>

## Features

*   **Authentication**: User login with username/password.
*   **Reverse Proxy**: Securely proxy requests to backend applications.
*   **Service Discovery**: Automatically discover services via Docker labels.
*   **Static Configuration**: Define services manually in `config.yml`.
*   **Centralized Security**: Enforce authentication for all your apps in one place.
*   **Admin UI**: Configure Moat and manage static services via web interface.
*   **Cookie-based Authentication**: Keeps users logged in across multiple apps.

## Prerequisites

*   Python 3.7+
*   Docker (optional, for service discovery)

## Installation

```bash
git clone https://github.com/your-username/moat.git
cd moat
python3 -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
pip install -r requirements.txt
```

## Configuration

Moat's configuration is managed through a `config.yml` file.  You can initialize a basic configuration file using the `init-config` command, or create one manually.

1.  **Initialize Configuration**:
    ```bash
    python main.py init-config
    ```
2.  **Edit `config.yml`**:
    *   Set a strong `secret_key`.  Use `openssl rand -hex 32` to generate one.
    *   Configure `moat_base_url` to the public URL where Moat is accessible.
    *   Adjust other settings as needed (database URL, cookie domain, etc.).

## Running Moat

```bash
python main.py run --reload # Use --reload for automatic restarts during development
```

## Usage

Once Moat is running, access its admin interface (typically at `/moat/admin`) to configure reverse proxy rules.

*   **Docker Service Discovery**:  Moat automatically detects Docker containers with specific labels.  See the Configuration section for details.
*   **Static Services**:  Define static proxy rules in `config.yml` or via the admin UI.

## CLI Commands

*   `init-config`: Creates a default `config.yml` file.
*   `run`: Starts the Moat server.  Use `--reload` for development.
*   `add-static`: Adds a static service entry to `config.yml`.

## Cloudflared (Cloudflare Tunnels) Setup

See [assets/cloudflared.md](assets/cloudflared.md) for instructions on how to set up Moat behind a Cloudflare Tunnel.

## Troubleshooting

* **"Secret key not configured" / "Moat configuration file not found"**: Ensure `config.yml` exists in the working directory and `secret_key` is set. Run `moat init-config`.
* **Redirect loops or incorrect login URL**: Double-check `moat_base_url` in `config.yml`. It must be the public URL of Moat itself.
* **Cookies not working across subdomains**: Verify `cookie_domain` is set correctly (e.g., `.yourdomain.com`).
* **Docker services not appearing**:
   * Ensure `docker_monitor_enabled: true`.
   * Check Moat's logs for Docker connection errors.
   * Verify container labels match `moat_label_prefix` and include `enable`, `hostname`, and `port`.
   * Ensure Moat has access to the Docker socket (`/var/run/docker.sock`).