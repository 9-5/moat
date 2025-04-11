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
<img src="https://github.com/user-attachments/assets/917da6b1-d226-40cb-9f44-af73-ca69934e5653/moat-admin-ui-config.png" width="800" height="auto">
</div>

## Features

- **Authentication**: User authentication to protect your services.
- **Reverse Proxy**: Routes external requests to internal services.
- **Centralized Configuration**: Manage all your service definitions in one place.
- **Docker Integration**: Automatically discover and proxy Docker containers based on labels.
- **Single Sign-On (SSO)**: Streamlined login experience across multiple services.
- **Admin UI**: web-based interface to manage users and settings.
## Prerequisites

*   Python 3.7+
*   Docker (if using Docker service discovery)

## Installation

```bash
git clone https://github.com/your-username/moat.git
cd moat
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Moat's configuration is managed via a `config.yml` file. You can generate a default configuration file using the CLI:

```bash
moat init-config
```

Edit `config.yml` to configure the following:

*   `listen_host`: The host Moat listens on (e.g., `0.0.0.0` or `127.0.0.1`).
*   `listen_port`: The port Moat listens on (e.g., `8000`).
*   `secret_key`: A randomly generated secret key for signing tokens.  **Important:** Change this to a strong, unique value.  Use `openssl rand -hex 32` to generate a secure key.
*   `database_url`: The URL of the SQLite database.
*   `moat_base_url`:  The public URL of your Moat instance (e.g., `https://moat.example.com`).  This is crucial if Moat is behind a reverse proxy or tunnel.  It tells Moat where it's being accessed from externally.
*   `cookie_domain`: The domain for cookies (e.g., `.example.com`).  This enables SSO across subdomains. If not using subdomains, specify the exact hostname.
*   `docker_monitor_enabled`:  Enable automatic service discovery from Docker labels.
*   `moat_label_prefix`: The prefix for Docker labels used by Moat (default: `moat`).
*   `static_services`:  Define static service mappings (hostname to internal URL).

Example `config.yml`:

```yaml
listen_host: 0.0.0.0
listen_port: 8000
secret_key: "YOUR_VERY_SECRET_KEY_CHANGE_THIS_NOW_PLEASE"
access_token_expire_minutes: 60
database_url: sqlite+aiosqlite:///./moat.db
moat_base_url: https://moat.example.com
cookie_domain: .example.com
docker_monitor_enabled: true
moat_label_prefix: moat
static_services:
  - hostname: app1.example.com
    target_url: http://localhost:8001
  - hostname: app2.example.com
    target_url: http://192.168.1.100:8002
```

## Running Moat

```bash
moat run
```

## Usage

Once Moat is running, access the admin UI at `/moat/admin` (e.g., `https://moat.example.com/moat/admin`). Create a user and define your services either via Docker labels or static configuration.

**Docker Labels:**

To automatically proxy a Docker container, add the following labels:

*   `moat.enable=true`
*   `moat.hostname=<your_desired_hostname>` (e.g., `app.example.com`)
*   `moat.port=<container_port>` (e.g., `80`)

Example `docker-compose.yml`:

```yaml
version: "3.8"
services:
  my_app:
    image: your-image
    ports:
      - "8000:80"
    labels:
      moat.enable: "true"
      moat.hostname: "app.example.com"
      moat.port: "80"
```

## CLI Commands

*   `moat init-config`:  Generates a default `config.yml` file.
*   `moat run`: Starts the Moat server.
*   `moat create-user <username>`: Creates a new user.  Prompts for password.
*   `moat delete-user <username>`: Deletes a user.
*   `moat add-static-service <public_hostname> <target_url>`: Adds a static service configuration.
*   `moat update-static-service <public_hostname> <target_url>`: Updates an existing static service's target URL.
*   `moat remove-static-service <public_hostname>`: Removes a static service configuration.
*   `moat docker bind <public_hostname> <container_name_or_id>`: Creates a static service entry bound to a Docker container's hostname and port, determined by labels.

## Troubleshooting

* **"Secret key not configured" / "Moat configuration file not found"**: Ensure `config.yml` exists in the working directory and `secret_key` is set. Run `moat init-config`.
* **Redirect loops or incorrect login URL**: Double-check `moat_base_url` in `config.yml`. It must be the public URL of Moat itself.
* **Cookies not working across subdomains**: Verify `cookie_domain` is set correctly (e.g., `.yourdomain.com`).
* **Docker services not appearing**:
   * Ensure `docker_monitor_enabled: true`.
   * Check Moat's logs for Docker connection errors.
   * Verify container labels match `moat_label_prefix` and include `enable`, `hostname`, and `port`.
   * Ensure Moat has access to the Docker socket (`/var/run/docker.sock`).