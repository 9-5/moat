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
<img src="https://github.com/user-attachments/assets/917da6b1-d226-40cb-9f44-b154-4754-8f7a-6a1950e43067/moat-login.png" width="300" />
<img src="https://github.com/user-attachments/assets/6e1185ff-9410-4dd3-bd72-5298b0743197/moat-admin.png" width="300" />
</div>

## Features

*   **Authentication**: User login with password protection.
*   **Reverse Proxy**: Routes traffic to backend services based on hostname.
*   **Service Discovery**: Automatically discovers services via Docker labels.
*   **Static Configuration**: Define services manually in the `config.yml` file.
*   **Admin UI**: Web interface to manage settings, create users, and view service status.
*	**Cloudflare Tunnel**: Guide to set up moat with Cloudflare tunnels for secure remote access.

## Prerequisites

*   Python 3.7+
*   Docker (if using Docker service discovery)

## Installation

```bash
git clone https://github.com/a7i/moat.git
cd moat
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
pip install -r requirements.txt
```

## Configuration

Moat uses a `config.yml` file for configuration. An example configuration is provided in `config.example.yml`.

1.  **Initialize Configuration**:
    ```bash
    moat init-config
    ```
2.  **Edit `config.yml`**:
    *   Set `secret_key` to a strong, randomly generated value.  You can use `openssl rand -hex 32` to generate one.
    *   Configure `database_url`, `moat_base_url`, and `cookie_domain` as needed.
    *   Adjust `docker_monitor_enabled` and `moat_label_prefix` if using Docker.
    *   Define static services in the `static_services` section if required.

## Running Moat

```bash
moat run
```

This starts the Moat server.  Access the admin UI at `/moat/admin` to create a user and configure settings.

## Usage

Once Moat is running, it will authenticate users and proxy requests to your backend services based on the configured hostnames.

*   **Docker Service Discovery**: Moat monitors Docker containers for labels matching `moat_label_prefix`.  A container is enabled if it has the `moat.enable=true` label, along with `moat.hostname` and `moat.port`.
*   **Static Services**:  Services defined in the `static_services` section of `config.yml` are always available.

## CLI Commands

Moat provides a command-line interface (CLI) for managing the application.

*   `moat init-config`: Creates a default `config.yml` if one does not exist.
*   `moat create-user`: Creates a new user in the database.
*   `moat run`: Starts the Moat server.
*	`moat add-static-service`: Adds a static service based on a running container.

## Troubleshooting

* **"Secret key not configured" / "Moat configuration file not found"**: Ensure `config.yml` exists in the working directory and `secret_key` is set. Run `moat init-config`.
* **Redirect loops or incorrect login URL**: Double-check `moat_base_url` in `config.yml`. It must be the public URL of Moat itself.
* **Cookies not working across subdomains**: Verify `cookie_domain` is set correctly (e.g., `.yourdomain.com`).
* **Docker services not appearing**:
   * Ensure `docker_monitor_enabled: true`.
   * Check Moat's logs for Docker connection errors.
   * Verify container labels match `moat_label_prefix` and include `enable`, `hostname`, and `port`.
   * Ensure Moat has access to the Docker socket (`/var/run/docker.sock`).