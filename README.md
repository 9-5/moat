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
<img src="https://github.com/user-attachments/assets/917da6b1-d226-40cb-9f44-b349-20c2f923e759/moat-dashboard.png" width="800px">
</div>
<div align="center">
<img src="https://github.com/user-attachments/assets/917da6b1-d226-40cb-9f44-b349-20c2f923e759/moat-login.png" width="400px">
</div>

## Features

- **Authentication**: Secure your applications with username/password authentication.
- **Reverse Proxy**: Route traffic to your applications based on hostname.
- **Service Discovery**: Automatically discover services via Docker labels (or define static services).
- **Single Sign-On (SSO)**: Users only need to log in once to access multiple applications.
- **Easy Configuration**: Configure Moat via a simple YAML file or through the web admin UI.
- **Docker Integration**: Seamlessly integrates with Dockerized applications.
- **Admin UI**: Web interface for managing users, services, and configuration.

## Prerequisites

- Python 3.7+
- Docker (optional, for Docker-based service discovery)

## Installation

```bash
git clone https://github.com/your-username/moat.git
cd moat
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Moat is configured via a `config.yml` file. An example configuration file (`config.example.yml`) is provided. Copy it and modify it to your needs:

```bash
cp config.example.yml config.yml
nano config.yml  # Edit the configuration file
```

Key configuration options:

- `listen_host`: The host Moat listens on (e.g., `0.0.0.0` for all interfaces).
- `listen_port`: The port Moat listens on (e.g., `8000`).
- `secret_key`: A randomly generated secret key used for signing access tokens (generate a secure key with `openssl rand -hex 32`).
- `database_url`: The URL of the SQLite database used to store user credentials.
- `moat_base_url`: The public URL of Moat itself (e.g., `https://moat.example.com`). **Important:** Set this correctly if Moat is behind a reverse proxy!
- `cookie_domain`: The domain for which the authentication cookie is valid (e.g., `.example.com` for all subdomains).

## Running Moat

First, initialize the database:

```bash
moat init-db
```

Then, start the Moat server:

```bash
moat run
```

## Usage

Once Moat is running, access the Moat admin UI in your browser (e.g., `https://moat.example.com/moat/admin`). Create a user and configure your services.

## CLI Commands

Moat provides a few command-line tools for managing the server:

*   `moat run`: Starts the Moat server.
*   `moat init-db`: Initializes the database.
*   `moat init-config`: Creates a default `config.yml` file if one doesn't exist.
*   `moat add-static-service --public-hostname <hostname> --target-url <url>`: Adds a static service to Moat's configuration.
*   `moat bind-static-service --public-hostname <hostname> <docker_container_name>`: Automatically binds a static service to a running Docker container.
*   `moat update-static-service --public-hostname <hostname> --target-url <url>`: Updates an existing static service's target URL.
*   `moat delete-static-service --public-hostname <hostname>`: Deletes a static service from Moat's configuration.

## Troubleshooting

* **"Secret key not configured" / "Moat configuration file not found"**: Ensure `config.yml` exists in the working directory and `secret_key` is set. Run `moat init-config`.
* **Redirect loops or incorrect login URL**: Double-check `moat_base_url` in `config.yml`. It must be the public URL of Moat itself.
* **Cookies not working across subdomains**: Verify `cookie_domain` is set correctly (e.g., `.yourdomain.com`).
* **Docker services not appearing**:
   * Ensure `docker_monitor_enabled: true`.
   * Check Moat's logs for Docker connection errors.
   * Verify container labels match `moat_label_prefix` and include `enable`, `hostname`, and `port`.
   * Ensure Moat has access to the Docker socket (`/var/run/docker.sock`).