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
<img src="https://github.com/user-attachments/assets/917da6b1-d226-40cb-9f44-97c1-31dd2d88e992/moat-admin-services.png" height="400" width="600"/>
</div>

## Features

*   **Authentication**: User login with username/password, cookie-based sessions.
*   **Reverse Proxy**: Routes traffic to internal services based on hostname.
*   **Service Discovery**: Automatically discovers services from Docker labels.
*   **Static Configuration**: Define services manually in a configuration file.
*   **Admin UI**: Web interface for managing configuration and services.
*   **Secure by Default**: Requires HTTPS for sensitive operations in production.

## Prerequisites

*   Python 3.7+
*   Docker (optional, for Docker-based service discovery)

## Installation

```bash
git clone https://github.com/your-username/moat.git
cd moat
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Moat is configured via a `config.yml` file. You can initialize a default configuration using the CLI:

```bash
moat init-config
```

Edit the `config.yml` file to set your desired settings, including:

*   `secret_key`: A randomly generated secret key for signing cookies.
*   `moat_base_url`: The public URL of your Moat instance (e.g., `https://moat.example.com`).
*   `cookie_domain`: The domain for cookies (e.g., `.example.com` for shared sessions across subdomains).
*   `database_url`: The URL for the SQLite database (e.g., `sqlite+aiosqlite:///./moat.db`).
*   `docker_monitor_enabled`: Enable/disable Docker service discovery.
*   `moat_label_prefix`: The prefix for Docker labels used to identify services.
*   `static_services`: Manually defined services.

See `config.example.yml` for a full list of available options.

## Running Moat

```bash
moat run
```

This will start the Moat server on the configured `listen_host` and `listen_port` (default: `0.0.0.0:8000`).

## Usage

Once Moat is running, you can access your protected services by navigating to their configured hostnames in your web browser. You will be redirected to the Moat login page if you are not already authenticated.

Moat uses cookies to maintain user sessions. The `cookie_domain` setting in `config.yml` controls the domain for these cookies. For single sign-on (SSO) across multiple subdomains, set `cookie_domain` to a domain prefixed with a dot (e.g., `.example.com`).

Moat automatically discovers services running in Docker containers that have labels matching the `moat_label_prefix` and the following:

*   `moat.enable=true`: Enables Moat for the service.
*   `moat.hostname=<hostname>`: The public hostname for the service (e.g., `app.example.com`).
*   `moat.port=<port>`: The port the service is listening on (e.g., `8080`).

You can also define services manually in the `static_services` section of `config.yml`.

## CLI Commands

Moat provides a CLI for managing configuration and users:

*   `moat init-config`: Initializes a default `config.yml` file.
*   `moat create-user <username>`: Creates a new user.

## Troubleshooting

* **"Secret key not configured" / "Moat configuration file not found"**: Ensure `config.yml` exists in the working directory and `secret_key` is set. Run `moat init-config`.
* **Redirect loops or incorrect login URL**: Double-check `moat_base_url` in `config.yml`. It must be the public URL of Moat itself.
* **Cookies not working across subdomains**: Verify `cookie_domain` is set correctly (e.g., `.yourdomain.com`).
* **Docker services not appearing**:
   * Ensure `docker_monitor_enabled: true`.
   * Check Moat's logs for Docker connection errors.
   * Verify container labels match `moat_label_prefix` and include `enable`, `hostname`, and `port`.
   * Ensure Moat has access to the Docker socket (`/var/run/docker.sock`).