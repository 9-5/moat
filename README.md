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
<img src="https://github.com/user-attachments/assets/917da6b1-d226-40cb-9f44-b500-452a-b5d2-93406d191664/moat-admin-dashboard.png" width="700"/>
</div>

## Features

- **Authentication**: User login and session management.
- **Reverse Proxy**: Routes requests to internal applications based on hostname.
- **Centralized Configuration**: Manage services and authentication from a single `config.yml` file or the web UI.
- **Docker Integration**: Automatically discover and proxy Docker containers via labels.
- **Admin UI**: Web interface for managing configuration and users.

## Prerequisites

- Python 3.7+
- Docker (if using Docker integration)

## Installation

1.  Clone the repository:

    ```bash
    git clone https://github.com/your-username/moat.git
    cd moat
    ```
2.  Create a virtual environment (recommended):

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate  # On Linux/macOS
    .venv\Scripts\activate  # On Windows
    ```
3.  Install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

## Configuration

Moat uses a `config.yml` file for configuration.  A sample configuration file (`config.example.yml`) is provided.

1.  **Initialize the configuration**:

    ```bash
    moat init-config
    ```

    This will create a `config.yml` file in the current directory.
2.  **Edit `config.yml`**:

    *   **`secret_key`**:  Generate a strong, random secret key using `openssl rand -hex 32` and set it in `config.yml`.  **This is crucial for security.**
    *   **`moat_base_url`**: The public URL of your Moat instance (e.g., `https://moat.example.com`).  Required if Moat is behind a reverse proxy or tunnel.
    *   **`cookie_domain`**:  The domain for which cookies should be set (e.g., `.example.com` for subdomains).
    *   **`docker_monitor_enabled`**: Set to `true` to enable automatic service discovery via Docker labels.
    *   **`moat_label_prefix`**:  The prefix for Docker labels used by Moat (default: `moat`).
    *   **`static_services`**:  Define static service mappings for applications not running in Docker or requiring specific configurations.

    ```yaml
    listen_host: "0.0.0.0"
    listen_port: 8000
    secret_key: "YOUR_VERY_SECRET_KEY_CHANGE_THIS_NOW_PLEASE" # Generate with: openssl rand -hex 32
    access_token_expire_minutes: 60
    database_url: "sqlite+aiosqlite:///./moat.db"
    moat_base_url: null # e.g., https://moat.yourdomain.com, required if behind a proxy/tunnel
    cookie_domain: null # e.g., .yourdomain.com
    docker_monitor_enabled: true
    moat_label_prefix: "moat"
    static_services:
    # - hostname: "app1.example.com"
    #   target_url: "http://localhost:3000"
    ```

## Running Moat

```bash
moat run
```

This will start the Moat server.  You can then access the Moat admin UI in your browser (e.g., `https://moat.example.com/moat/admin`).

## Usage

1.  **Create a user**: Use the `moat create-user` CLI command to create an initial user account.

    ```bash
    moat create-user --username admin --password securepassword
    ```
2.  **Configure services**:
    *   **Docker**:  For Docker services, add labels to your containers:

        ```yaml
        labels:
          moat.enable: "true"
          moat.hostname: "app.example.com"
          moat.port: "3000"
        ```

        Replace `app.example.com` with the desired hostname and `3000` with the container's port.
    *   **Static Services**:  Add entries to the `static_services` section of `config.yml`.
3.  **Access your applications**:  Once configured, Moat will handle authentication and proxy requests to your applications based on the hostname.

## CLI Commands

*   `moat init-config`: Creates a default `config.yml` file.
*   `moat run`: Starts the Moat server.
*   `moat create-user`: Creates a new user account.
*   `moat add-static-service`: Adds a static service entry to `config.yml`.
*   `moat update-static-service`: Updates a static service entry in `config.yml`.
*   `moat delete-static-service`: Deletes a static service entry from `config.yml`.

## Troubleshooting

* **"Secret key not configured" / "Moat configuration file not found"**: Ensure `config.yml` exists in the working directory and `secret_key` is set. Run `moat init-config`.
* **Redirect loops or incorrect login URL**: Double-check `moat_base_url` in `config.yml`. It must be the public URL of Moat itself.
* **Cookies not working across subdomains**: Verify `cookie_domain` is set correctly (e.g., `.yourdomain.com`).
* **Docker services not appearing**:
   * Ensure `docker_monitor_enabled: true`.
   * Check Moat's logs for Docker connection errors.
   * Verify container labels match `moat_label_prefix` and include `enable`, `hostname`, and `port`.
   * Ensure Moat has access to the Docker socket (`/var/run/docker.sock`).