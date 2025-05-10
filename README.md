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
<img src="https://github.com/user-attachments/assets/917da6b1-d226-40cb-9f44-bc73-439e-9e10-4596809940c4/moat-admin-dashboard.png" height="300" width="600"/>
<img src="https://github.com/user-attachments/assets/917da6b1-d226-40cb-9f44-bc73-439e-9e10-4596809940c4/moat-login-page.png" height="300" width="600"/>
</div>

## Features

*   **Authentication**: Secure your applications with username/password authentication.
*   **Reverse Proxy**: Route traffic to your internal services based on hostname.
*   **Centralized Configuration**: Manage services and authentication from a single `config.yml` file or Admin UI.
*   **Docker Integration**: Automatically discover and proxy Docker containers based on labels.
*   **Single Sign-On (SSO)**: Authenticate once and access multiple applications without re-logging in.
*   **Admin UI**: Web interface for managing users, services, and configuration.
*   **Easy Setup**: Simple configuration and deployment, get started in minutes.

## Prerequisites

*   Python 3.7+
*   Docker (optional, for Docker-based service discovery)

## Installation

1.  Clone the repository:

    ```bash
    git clone https://github.com/your-username/moat.git
    cd moat
    ```

2.  Create a virtual environment:

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  Install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

## Configuration

Moat is configured via a `config.yml` file in the working directory. You can create a default configuration using the CLI:

```bash
moat init-config
```

Edit the `config.yml` file to match your environment. Key settings include:

*   `secret_key`: A randomly generated secret key for signing cookies.  **IMPORTANT:** Change this to a strong, unique value. Generate with `openssl rand -hex 32`.
*   `moat_base_url`: The public URL of your Moat instance (e.g., `https://moat.example.com`). This is crucial for correct redirects and cookie handling.
*   `cookie_domain`:  The domain for which Moat's cookies will be valid (e.g., `.example.com` for all subdomains, or `app.example.com` for a specific application).
*   `docker_monitor_enabled`:  Enable or disable automatic service discovery via Docker labels.
*   `static_services`:  A list of static service definitions, mapping hostnames to internal URLs.

Example `config.yml`:

```yaml
listen_host: 0.0.0.0
listen_port: 8000
secret_key: YOUR_VERY_SECRET_KEY  # CHANGE THIS!
access_token_expire_minutes: 60
database_url: sqlite+aiosqlite:///./moat.db
moat_base_url: https://moat.example.com
cookie_domain: .example.com
docker_monitor_enabled: true
moat_label_prefix: moat
static_services:
  - hostname: app1.example.com
    target_url: http://localhost:3000
  - hostname: app2.example.com
    target_url: http://localhost:3001
```

## Running Moat

To start the Moat server, use the CLI:

```bash
moat run
```

This will start the server on the configured `listen_host` and `listen_port`.

## Usage

Once Moat is running, you can access your protected applications by navigating to their configured hostnames in your web browser. You will be redirected to Moat's login page if you are not already authenticated.

## CLI Commands

Moat provides a command-line interface for managing configuration and users.

*   `moat init-config`: Creates a default `config.yml` file.
*   `moat run`: Starts the Moat server.
*   `moat create-user <username> <password>`: Creates a new user in the database.
*   `moat add-static-service <public_hostname> <target_url>`: Adds a static service entry to the configuration.

## Troubleshooting

* **"Secret key not configured" / "Moat configuration file not found"**: Ensure `config.yml` exists in the working directory and `secret_key` is set. Run `moat init-config`.
* **Redirect loops or incorrect login URL**: Double-check `moat_base_url` in `config.yml`. It must be the public URL of Moat itself.
* **Cookies not working across subdomains**: Verify `cookie_domain` is set correctly (e.g., `.yourdomain.com`).
* **Docker services not appearing**:
   * Ensure `docker_monitor_enabled: true`.
   * Check Moat's logs for Docker connection errors.
   * Verify container labels match `moat_label_prefix` and include `enable`, `hostname`, and `port`.
   * Ensure Moat has access to the Docker socket (`/var/run/docker.sock`).