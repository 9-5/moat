<p align="center"><img src="assets\moat.png" height="250" width="250"/></p>

# Moat - Build a moat around your self-hosted apps.

Moat is a lightweight, FastAPI-based security gateway that provides authentication and reverse proxying capabilities for your web services. It can manage service discovery through Docker labels or static configuration.

## Table of Contents

[Screenshots](#screenshots)

[Features](#features)

[Prerequisites](#prerequisites]

[Installation](#installation)

[Configuration](#configuration)

[Running Moat](#running-moat)

[Usage](#usage)

[CLI Commands](#cli-commands)

[Troubleshooting](#troubleshooting)

## Screenshots
<div align="center">
<img src="https://github.com/user-attachments/assets/917da6b1-d226-40cb-9f44-e17d-4701-9c53-ef87f9038e1a/moat-admin-page.png" width="700"/>
<img src="https://github.com/user-attachments/assets/d5ef7111-4375-4021-951f-2932782a92a8/moat-login-page.png" width="700"/>
</div>

## Features

*   **Authentication**: Secure your applications with username/password authentication.
*   **Reverse Proxy**: Route traffic to your applications based on hostname.
*   **Centralized Management**: Configure services and authentication through a web UI or YAML file.
*   **Docker Integration**: Automatically discover and proxy Docker containers using labels.
*   **Single Sign-On (SSO)**: Share authentication across multiple applications using cookies.

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

Moat is configured via a `config.yml` file. You can create a default configuration using the CLI:

```bash
moat init-config
```

Edit the `config.yml` file to set your desired settings, including:

*   `secret_key`: A randomly generated secret key used for signing cookies.  **Important**: Change this to a unique, strong value.
*   `moat_base_url`: The public URL of your Moat instance (e.g., `https://moat.example.com`).  This is important if Moat is behind a reverse proxy or tunnel.
*   `cookie_domain`: The domain for which cookies should be valid (e.g., `.example.com` for all subdomains).
*   `database_url`: The URL for the database where user credentials are stored (default: `sqlite+aiosqlite:///./moat.db`).

Example `config.yml`:

```yaml
listen_host: "0.0.0.0"
listen_port: 8000
secret_key: "YOUR_VERY_SECRET_KEY_CHANGE_THIS_NOW_PLEASE" # Generate with: openssl rand -hex 32
access_token_expire_minutes: 60
database_url: "sqlite+aiosqlite:///./moat.db"
moat_base_url: "https://moat.example.com"
cookie_domain: ".example.com"
docker_monitor_enabled: true
moat_label_prefix: "moat"
static_services:
  - hostname: "app1.example.com"
    target_url: "http://localhost:3000"
  - hostname: "app2.example.com"
    target_url: "http://192.168.1.100:8080"
```

## Running Moat

```bash
moat run
```

This will start the Moat server.  Access the admin UI at `http://localhost:8000/moat/admin` (or your configured `listen_host` and `listen_port`) to create users and configure services.

## Usage

Once Moat is running, you can access your protected services through Moat.  Moat will automatically redirect unauthenticated users to the login page.

### Docker Service Discovery

To automatically discover and proxy Docker containers, enable `docker_monitor_enabled` in `config.yml` and add the following labels to your containers:

*   `moat.enable=true`:  Enable Moat proxying for this container.
*   `moat.hostname=<your_hostname>`: The public hostname for this service (e.g., `app.example.com`).
*   `moat.port=<port_number>`:  The port the container is listening on.

For example:

```yaml
version: "3.8"
services:
  my-app:
    image: my-app:latest
    labels:
      moat.enable: "true"
      moat.hostname: "app.example.com"
      moat.port: "3000"
```

Moat will automatically create a reverse proxy for `app.example.com` that forwards traffic to port 3000 of the `my-app` container.

## CLI Commands

*   `moat run`: Starts the Moat server.
*   `moat init-config`: Creates a default `config.yml` file.
*   `moat create-user <username>`: Creates a new user.  You will be prompted for a password.
*   `moat add-static-service <public_hostname> <target_url>`: Adds a static service configuration to `config.yml`.
*   `moat bind <public_hostname> <container_name>`: Adds a static service bound to a Docker container.

## Troubleshooting

* **"Secret key not configured" / "Moat configuration file not found"**: Ensure `config.yml` exists in the working directory and `secret_key` is set. Run `moat init-config`.
* **Redirect loops or incorrect login URL**: Double-check `moat_base_url` in `config.yml`. It must be the public URL of Moat itself.
* **Cookies not working across subdomains**: Verify `cookie_domain` is set correctly (e.g., `.yourdomain.com`).
* **Docker services not appearing**:
   * Ensure `docker_monitor_enabled: true`.
   * Check Moat's logs for Docker connection errors.
   * Verify container labels match `moat_label_prefix` and include `enable`, `hostname`, and `port`.
   * Ensure Moat has access to the Docker socket (`/var/run/docker.sock`).