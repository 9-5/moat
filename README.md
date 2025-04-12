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
<img src="https://github.com/user-attachments/assets/917da6b1-d226-40cb-9f44-a7e1-a1526c3a94d6/moat-admin-panel.png" width="700"/>
</div>

## Features

-   **Authentication**: Uses username/password authentication to protect your services.
-   **Reverse Proxy**: Acts as a reverse proxy, routing traffic to your backend services after successful authentication.
-   **Centralized Configuration**: Manages service definitions and authentication settings in a single `config.yml` file.
-   **Docker Integration**: Automatically discovers and proxies Docker containers based on labels.
-   **Static Service Definitions**: Allows defining static service targets for non-Dockerized applications.
-   **Single Sign-On (SSO)**: Provides a single login point for all your protected services via cookie-based authentication.
-   **Admin UI**: Web interface for managing configuration.
-   **CLI Tooling**: CLI for user management and configuration.

## Prerequisites

-   Python 3.7+
-   Docker (optional, for Docker-based service discovery)

## Installation

```bash
git clone https://github.com/Singularity-Now/moat.git
cd moat
python3 -m venv venv
source venv/bin/activate  # Or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

## Configuration

Moat's configuration is managed via a `config.yml` file. You can create a default configuration file using the CLI:

```bash
moat init-config
```

This will generate a `config.yml` file with default settings.  Edit this file to configure your services, authentication settings, and other options.  See `config.example.yml` for an example configuration.  **IMPORTANT:** Change the `secret_key` to a strong, randomly generated value.

## Running Moat

To start the Moat server, use the `run` command:

```bash
moat run
```

This will start the Moat server using the settings in your `config.yml` file.

## Usage

Once Moat is running, access it through your configured `moat_base_url`.  You will be prompted to log in.  After logging in, you can access your protected services.

Moat automatically discovers Docker containers with the specified labels (if Docker integration is enabled).  For non-Dockerized applications, you can define static service targets in the `config.yml` file.

## CLI Commands

Moat provides a command-line interface (CLI) for managing the application:

*   `moat init-config`: Creates a default `config.yml` file.
*   `moat run`: Starts the Moat server.
*   `moat create-user <username>`: Creates a new user.  You will be prompted for a password.
*   `moat add-static-service <public_hostname> <target_url>`: Adds a static service definition to the config.
*   `moat update-static-service <public_hostname> <new_target_url>`: Updates a static service definition.
*   `moat bind-docker <public_hostname> <container_name>`: Automatically bind a static service to a running docker container.
*   `moat health`: Shows the current status and checks if the Docker daemon is running.

## Troubleshooting

* **"Secret key not configured" / "Moat configuration file not found"**: Ensure `config.yml` exists in the working directory and `secret_key` is set. Run `moat init-config`.
* **Redirect loops or incorrect login URL**: Double-check `moat_base_url` in `config.yml`. It must be the public URL of Moat itself.
* **Cookies not working across subdomains**: Verify `cookie_domain` is set correctly (e.g., `.yourdomain.com`).
* **Docker services not appearing**:
   * Ensure `docker_monitor_enabled: true`.
   * Check Moat's logs for Docker connection errors.
   * Verify container labels match `moat_label_prefix` and include `enable`, `hostname`, and `port`.
   * Ensure Moat has access to the Docker socket (`/var/run/docker.sock`).