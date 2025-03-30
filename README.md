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
<img src="https://github.com/user-attachments/assets/917da6b1-d226-40cb-9f44-9b8a-465320f42c48/moat-admin-services.png" height="300" width="600"/>
<img src="https://github.com/user-attachments/assets/65551439-47b3-45c4-a187-0a611597f896/moat-login.png" height="300" width="600"/>
</div>

## Features

*   **Authentication**: Secure your applications with username/password authentication.
*   **Reverse Proxy**: Route traffic to your internal services based on hostname.
*   **Automatic Service Discovery**: Automatically detect and proxy Docker containers based on labels.
*   **Centralized Configuration**: Manage all your services and authentication settings in one place.
*   **Admin UI**: Web interface for easy configuration and management.
*   **Single Sign-On (SSO)**: Users only need to log in once to access multiple applications.
*   **Configurable Cookie Domain**: Supports setting a cookie domain for subdomains.

## Prerequisites

*   Python 3.8+
*   Docker (if using Docker service discovery)

## Installation

1.  Clone the repository:

    ```bash
    git clone https://github.com/your-username/moat.git
    cd moat
    ```
2.  Create a virtual environment:

    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Linux/macOS
    .venv\Scripts\activate  # On Windows
    ```
3.  Install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

## Configuration

1.  Initialize the configuration file:

    ```bash
    moat init-config
    ```

2.  Edit the `config.yml` file to configure Moat. See the [Configuration](#configuration) section for details.

## Running Moat

```bash
moat run
```

## Usage

Once Moat is running, access the admin UI at `http://<moat_base_url>/moat/admin` to configure your services and users.

## CLI Commands

*   `moat run`: Starts the Moat server.
*   `moat init-config`: Creates a default `config.yml` file.
*   `moat create-user <username>`: Creates a new user. Prompts for password.
*   `moat update-user <username>`: Updates an existing user's password.
*   `moat list-services`: Lists services.
*   `moat add-static-service <hostname> <target_url>`: Adds a static service entry.
*   `moat bind-docker-service <hostname> <container_name>`: Binds a hostname to a docker container, auto-configuring a static service.

## Configuration

The `config.yml` file contains the following settings:

*   `listen_host`: The host Moat listens on (default: `0.0.0.0`).
*   `listen_port`: The port Moat listens on (default: `8000`).
*   `secret_key`: A secret key used for signing access tokens.  **IMPORTANT: Change this to a randomly generated, strong key!**
*   `access_token_expire_minutes`:  Lifetime of access tokens in minutes (default: 60).
*   `database_url`: The URL of the SQLite database (default: `sqlite+aiosqlite:///./moat.db`).
*   `moat_base_url`: The public URL of Moat itself (e.g., `https://moat.yourdomain.com`).  This is crucial if Moat is behind a reverse proxy.
*   `cookie_domain`: The domain for which cookies are valid (e.g., `.yourdomain.com` for SSO across subdomains, or `yourdomain.com` for a single domain).
*   `docker_monitor_enabled`: Whether to automatically discover services from Docker labels (default: `true`).
*   `moat_label_prefix`: The prefix for Docker labels used by Moat (default: `moat`).
*   `static_services`: A list of statically configured services.

### Static Service Configuration

Static services are defined as a list of dictionaries, each with a `hostname` and a `target_url`.  For example:

```yaml
static_services:
  - hostname: app1.example.com
    target_url: http://localhost:3000
  - hostname: app2.example.com
    target_url: http://192.168.1.100:8080
```

### Docker Label Configuration

Moat uses Docker labels to automatically discover and proxy services. To enable a service, add the following labels to your Docker container:

*   `moat.enable=true`: Enables Moat proxying for this container.
*   `moat.hostname=<your_hostname>`: The hostname to use for this service (e.g., `app.example.com`).
*   `moat.port=<container_port>`:  The port the container exposes (e.g., `80`).

For example:

```yaml
version: "3.9"
services:
  my-app:
    image: my-app:latest
    labels:
      moat.enable: "true"
      moat.hostname: "app.example.com"
      moat.port: "80"
```

You can also set a custom label prefix using the `moat_label_prefix` setting in `config.yml`.

## Troubleshooting

* **"Secret key not configured" / "Moat configuration file not found"**: Ensure `config.yml` exists in the working directory and `secret_key` is set. Run `moat init-config`.
* **Redirect loops or incorrect login URL**: Double-check `moat_base_url` in `config.yml`. It must be the public URL of Moat itself.
* **Cookies not working across subdomains**: Verify `cookie_domain` is set correctly (e.g., `.yourdomain.com`).
* **Docker services not appearing**:
   * Ensure `docker_monitor_enabled: true`.
   * Check Moat's logs for Docker connection errors.
   * Verify container labels match `moat_label_prefix` and include `enable`, `hostname`, and `port`.
   * Ensure Moat has access to the Docker socket (`/var/run/docker.sock`).