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
<img src="https://github.com/user-attachments/assets/917da6b1-d226-40cb-9f44-a263-bc0905722518/moat-admin-login.png" width="400">
<img src="https://github.com/user-attachments/assets/1595c257-c9f9-46a8-bc2f-6445098b6f56/moat-admin-config.png" width="400">
</div>

## Features

*   **Authentication:** Protect your services with a login page.
*   **Reverse Proxy:** Route requests to your internal services.
*   **Service Discovery:** Automatically discover services via Docker labels.
*   **Static Configuration:** Define services manually.
*   **Single Sign-On (SSO):** Share authentication across multiple services using cookies.
*   **Admin UI:** Web-based interface for configuration and user management.

## Prerequisites

*   Python 3.7+
*   Docker (optional, for Docker-based service discovery)

## Installation

```bash
pip install "moat[all]"
```

## Configuration

Moat requires a `config.yml` file in the working directory. You can generate a default configuration file using the CLI:

```bash
moat init-config
```

Edit the `config.yml` file to configure Moat.  **IMPORTANT:** Change the `secret_key` to a strong, randomly generated value.

## Running Moat

```bash
moat run
```

## Usage

Once Moat is running, access the admin UI at `http://localhost:8000/moat/admin`.  Log in to configure services and manage users.  Then, access your protected services through the hostnames you've configured.

## CLI Commands

Moat provides a command-line interface for managing the configuration and services:

*   `moat init-config`: Create a default `config.yml` file.
*   `moat run`: Start the Moat server.
*   `moat add-user <username>`: Create a new user.
*   `moat set-password <username>`: Set a user's password.
*   `moat add-static-service <hostname> <target_url>`: Add a static service.
*   `moat update-static-service <hostname> <target_url>`: Update a static service.

## Troubleshooting

* **"Secret key not configured" / "Moat configuration file not found"**: Ensure `config.yml` exists in the working directory and `secret_key` is set. Run `moat init-config`.
* **Redirect loops or incorrect login URL**: Double-check `moat_base_url` in `config.yml`. It must be the public URL of Moat itself.
* **Cookies not working across subdomains**: Verify `cookie_domain` is set correctly (e.g., `.yourdomain.com`).
* **Docker services not appearing**:
   * Ensure `docker_monitor_enabled: true`.
   * Check Moat's logs for Docker connection errors.
   * Verify container labels match `moat_label_prefix` and include `enable`, `hostname`, and `port`.
   * Ensure Moat has access to the Docker socket (`/var/run/docker.sock`).