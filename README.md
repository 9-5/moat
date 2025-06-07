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
<img src="https://github.com/user-attachments/assets/917da6b1-d226-40cb-9f44-4b98-b4c9-0507e5481d1a/moat-admin-ui.png" height="400" width="600"/>
<img src="https://github.com/user-attachments/assets/54917097-c8a8-4016-b714-53f6d69c64b2/moat-login-page.png" height="400" width="600"/>
</div>

## Features

*   **Authentication**: Secure your applications with username/password authentication.
*   **Reverse Proxy**: Route traffic to your applications based on hostname.
*   **Centralized Configuration**: Manage your services and authentication settings in one place.
*   **Docker Integration**: Automatically discover and proxy Docker containers based on labels.
*   **Single Sign-On (SSO)**: Log in once and access all your applications without re-authenticating.

## Prerequisites

*   Python 3.7+
*   Docker (optional, for Docker-based service discovery)

## Installation

```bash
git clone https://github.com/your-username/moat.git
cd moat
python -m venv venv
source venv/bin/activate # On Windows, use `venv\Scripts\activate`
pip install -r requirements.txt
```

## Configuration

Moat's configuration is managed through a `config.yml` file. You can generate a default configuration file using the CLI:

```bash
moat init-config
```

Edit the `config.yml` file to configure your services, authentication settings, and other options.  See `config.example.yml` for documentation on all available options.

Key settings:

*   `listen_host`: The host Moat listens on (default: `0.0.0.0`).
*   `listen_port`: The port Moat listens on (default: `8000`).
*   `secret_key`: A randomly generated secret key for signing tokens.  **Important**: Change this to a unique, strong value.
*   `database_url`: The URL of the SQLite database (default: `sqlite+aiosqlite:///./moat.db`).
*   `moat_base_url`:  The public-facing base URL where Moat is accessible.  This is crucial if Moat sits behind a reverse proxy or tunnel.  Example: `https://moat.example.com`.
*   `cookie_domain`:  The domain for the authentication cookie.  Use a leading dot for subdomains (e.g., `.example.com`).  If unset, cookies are specific to the exact hostname.
*   `docker_monitor_enabled`:  Enable or disable Docker service discovery (default: `true`).
*   `moat_label_prefix`:  The prefix for Docker labels used to identify services (default: `moat`).

## Running Moat

Start the Moat server using the CLI:

```bash
moat run
```

By default, Moat runs on `http://localhost:8000`.

## Usage

Once Moat is running, you can access your protected services through Moat's reverse proxy.  The exact URLs depend on your configuration, but typically follow this pattern:

```
http://<hostname_defined_in_config>
```

If authentication is required, you will be redirected to Moat's login page. After successful login, you will be redirected back to the requested service.

## CLI Commands

Moat provides a command-line interface (CLI) for managing the server and configuration.

*   `moat init-config`: Generates a default `config.yml` file.
*   `moat run`: Starts the Moat server.
*   `moat add-static-service <container_name> <public_hostname> <container_port>`: Adds a static service entry based on a running Docker container.
    *   Example: `moat add-static-service my-app app.example.com 8080`
    *   **Note**: Requires Docker to be running and accessible.  The `container_name` must match the container's actual name (not ID).
*   `moat create-user <username>`: Creates a new user. The CLI will prompt for a password.

## Troubleshooting

* **"Secret key not configured" / "Moat configuration file not found"**: Ensure `config.yml` exists in the working directory and `secret_key` is set. Run `moat init-config`.
* **Redirect loops or incorrect login URL**: Double-check `moat_base_url` in `config.yml`. It must be the public URL of Moat itself.
* **Cookies not working across subdomains**: Verify `cookie_domain` is set correctly (e.g., `.yourdomain.com`).
* **Docker services not appearing**:
   * Ensure `docker_monitor_enabled: true`.
   * Check Moat's logs for Docker connection errors.
   * Verify container labels match `moat_label_prefix` and include `enable`, `hostname`, and `port`.
   * Ensure Moat has access to the Docker socket (`/var/run/docker.sock`).