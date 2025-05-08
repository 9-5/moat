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
<img src="https://github.com/user-attachments/assets/917da6b1-d226-40cb-9f44-b471-265c772c3b97/Moat_Dashboard.png" width="700"/>
</div>

## Features

*   **Authentication**: User authentication using username/password.
*   **Reverse Proxy**: Proxies requests to backend services after successful authentication.
*   **Centralized Security**: Enforces security policies at a single point.
*   **Docker Integration**: Automatically discovers and proxies Docker containers based on labels.
*   **Static Configuration**: Supports statically defined backend services.
*   **Single Sign-On (SSO)**: Provides a single login point for multiple applications.
*   **Admin UI**: Web interface for configuration and management.

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

1.  Copy `config.example.yml` to `config.yml`.
2.  Edit `config.yml` to set the `secret_key`, `moat_base_url`, and other settings.
3.  For Docker integration, ensure Docker is running and Moat has access to the Docker socket.

## Running Moat

```bash
moat init-config # if config.yml doesn't exist
moat run
```

## Usage

Once Moat is running, access the admin UI at `moat_base_url/moat/admin`.  Log in with a user created using the CLI `moat create-user`.  Configure backend services either statically in `config.yml` or dynamically using Docker labels.  Access your applications through Moat's reverse proxy.

## CLI Commands

*   `moat init-config`: Initializes a default `config.yml` file.
*   `moat create-user`: Creates a new user.
*   `moat run`: Starts the Moat server.
*   `moat add-static`: Adds a static service to the config.
*   `moat update-static`: Updates a static service in the config.

## Troubleshooting

* **"Secret key not configured" / "Moat configuration file not found"**: Ensure `config.yml` exists in the working directory and `secret_key` is set. Run `moat init-config`.
* **Redirect loops or incorrect login URL**: Double-check `moat_base_url` in `config.yml`. It must be the public URL of Moat itself.
* **Cookies not working across subdomains**: Verify `cookie_domain` is set correctly (e.g., `.yourdomain.com`).
* **Docker services not appearing**:
   * Ensure `docker_monitor_enabled: true`.
   * Check Moat's logs for Docker connection errors.
   * Verify container labels match `moat_label_prefix` and include `enable`, `hostname`, and `port`.
   * Ensure Moat has access to the Docker socket (`/var/run/docker.sock`).