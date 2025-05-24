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
<img src="https://github.com/user-attachments/assets/917da6b1-d226-40cb-9f44-4dd8-41bd-8a76-055efb922319/moat-login.png" height="300" width="600"/>
<img src="https://github.com/user-attachments/assets/917da6b1-d226-40cb-9f44-4dd8-41bd-8a76-055efb922319/moat-admin.png" height="300" width="600"/>
</div>

## Features

*   **Authentication**: User login with password protection.
*   **Reverse Proxy**: Routes traffic to backend services based on hostname.
*   **Docker Integration**: Automatically discovers and proxies Docker containers.
*   **Centralized Configuration**: Manage settings via a single `config.yml` file and an admin UI.
*   **Single Sign-On (SSO)**: Streamlines access to multiple applications.
*   **Admin UI**: Web interface for configuring Moat.
*   **CLI Tools**: Command-line interface for initialization and management.

## Prerequisites

*   Python 3.9+
*   Docker (optional, for Docker integration)

## Installation

1.  Clone the repository:

    ```bash
    git clone https://github.com/your-username/moat.git
    cd moat
    ```
2.  Create a virtual environment:

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```
3.  Install the dependencies:

    ```bash
    pip install -r requirements.txt
    ```

## Configuration

1.  Initialize the configuration file:

    ```bash
    moat init-config
    ```

    This creates a `config.yml` file in your working directory.
2.  Edit `config.yml` to set the `secret_key`, `moat_base_url`, `cookie_domain`, and other settings.  **Important:**  Set a strong, randomly generated `secret_key`.
    ```bash
    openssl rand -hex 32
    ```
3. Configure static services or docker integration as required.

## Running Moat

```bash
moat run
```

This starts the Moat server.  You can optionally specify the host and port:

```bash
moat run --host 0.0.0.0 --port 8080
```

## Usage

Once Moat is running, access the admin UI to configure users and services.  The admin UI is typically located at `/moat/admin` on your Moat instance (e.g., `https://moat.yourdomain.com/moat/admin`).

1.  **Create a User:** Use the `moat create-user` CLI command to create an initial user account.
2.  **Configure Services:** Add static service definitions in `config.yml` or enable Docker integration to automatically discover services.
3.  **Access Applications:** Access your applications through the hostnames you configured (e.g., `app.yourdomain.com`).  Moat will redirect unauthenticated users to the login page.

## CLI Commands

*   `moat run`: Starts the Moat server.
*   `moat init-config`: Creates a default `config.yml` file.
*   `moat create-user`: Creates a new user account.
*   `moat add-static`:  Adds a static service to the config file.
*   `moat docker:bind`:  Adds a static service bound to a docker container to the config file.

## Troubleshooting

* **"Secret key not configured" / "Moat configuration file not found"**: Ensure `config.yml` exists in the working directory and `secret_key` is set. Run `moat init-config`.
* **Redirect loops or incorrect login URL**: Double-check `moat_base_url` in `config.yml`. It must be the public URL of Moat itself.
* **Cookies not working across subdomains**: Verify `cookie_domain` is set correctly (e.g., `.yourdomain.com`).
* **Docker services not appearing**:
   * Ensure `docker_monitor_enabled: true`.
   * Check Moat's logs for Docker connection errors.
   * Verify container labels match `moat_label_prefix` and include `enable`, `hostname`, and `port`.
   * Ensure Moat has access to the Docker socket (`/var/run/docker.sock`).