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
<img src="https://github.com/user-attachments/assets/917da6b1-d226-40cb-9f44-b551-625f362f547a/moat-login.png" width="400" height="250">
<img src="https://github.com/user-attachments/assets/917da6b1-d226-40cb-9f44-b551-625f362f547a/moat-admin.png" width="400" height="250">
</div>

## Features

*   **Authentication**: Enforces authentication for your services.
*   **Reverse Proxy**: Routes traffic to your backend applications.
*   **Centralized Configuration**: Manage services via a single `config.yml` file or Docker labels.
*   **Docker Integration**: Automatically discovers and proxies Docker containers based on labels.
*   **Admin UI**: Web interface to configure Moat.
*   **Single Sign-On (SSO)**: Supports single sign-on across multiple services.
*   **Basic user management:** Create users and passwords via CLI
*   **Secure Cookie Handling**: Properly configured cookies for various deployment scenarios (subdomains, HTTPS).

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

Moat is configured via a `config.yml` file. An example configuration is provided in `config.example.yml`. To create a configuration file:

```bash
moat init-config
```

Edit the `config.yml` file to match your environment.

Key configuration options:

*   `listen_host`: The host Moat listens on (default: `0.0.0.0`).
*   `listen_port`: The port Moat listens on (default: `8000`).
*   `secret_key`: A randomly generated secret key used for signing access tokens.  **Important:** Change this to a strong, unique value!
*   `database_url`: The URL of the SQLite database (default: `sqlite+aiosqlite:///./moat.db`).
*   `moat_base_url`: The public URL of Moat itself. This is important when Moat is behind a reverse proxy or tunnel.
*   `cookie_domain`:  The domain for cookies (e.g., `.yourdomain.com`).  Set this to enable SSO across subdomains.
*   `docker_monitor_enabled`: Whether to monitor Docker for service discovery (default: `true`).
*   `moat_label_prefix`: The prefix for Docker labels used to configure services (default: `moat`).
*   `static_services`: A list of statically defined services (hostname and target URL).

## Running Moat

```bash
moat run
```

## Usage

Once Moat is running, access it via your configured `moat_base_url`.  You'll be prompted to log in.  After logging in, Moat will reverse proxy requests to your configured services.

### Docker Service Configuration

To expose a Docker container through Moat, add the following labels to your container:

*   `moat.enable=true`:  Enables Moat proxying for this container.
*   `moat.hostname=<public_hostname>`:  The public hostname for the service (e.g., `app.yourdomain.com`).
*   `moat.port=<container_port>`:  The port the container exposes (e.g., `80`).

Example `docker-compose.yml`:

```yaml
version: "3.9"
services:
  my-app:
    image: your-image
    ports:
      - "80:80"
    labels:
      moat.enable: "true"
      moat.hostname: "app.yourdomain.com"
      moat.port: "80"
```

### Static Service Configuration

You can also define services statically in `config.yml` using the `static_services` section. This is useful for services that are not running in Docker or for fixed targets.

Example:

```yaml
static_services:
  - hostname: "service1.yourdomain.com"
    target_url: "http://127.0.0.1:9001"
  - hostname: "another.example.com"
    target_url: "http://192.168.1.100:8080"
```

## CLI Commands

*   `moat run`: Starts the Moat server.
*   `moat init-config`: Creates a default `config.yml` file.
*   `moat create-user <username>`: Creates a new user. Prompts for a password.
*   `moat delete-user <username>`: Deletes an existing user.
*   `moat set-password <username>`: Changes a user's password.
*   `moat add-static-service <public_hostname> <target_url>`: Adds a static service entry to the config.
*   `moat update-static-service <public_hostname> <target_url>`: Updates a static service entry in the config.
*   `moat remove-static-service <public_hostname>`: Removes a static service entry from the config.

## Troubleshooting

* **"Secret key not configured" / "Moat configuration file not found"**: Ensure `config.yml` exists in the working directory and `secret_key` is set. Run `moat init-config`.
* **Redirect loops or incorrect login URL**: Double-check `moat_base_url` in `config.yml`. It must be the public URL of Moat itself.
* **Cookies not working across subdomains**: Verify `cookie_domain` is set correctly (e.g., `.yourdomain.com`).
* **Docker services not appearing**:
   * Ensure `docker_monitor_enabled: true`.
   * Check Moat's logs for Docker connection errors.
   * Verify container labels match `moat_label_prefix` and include `enable`, `hostname`, and `port`.
   * Ensure Moat has access to the Docker socket (`/var/run/docker.sock`).