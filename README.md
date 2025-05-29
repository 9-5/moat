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
<img src="https://github.com/user-attachments/assets/917da6b1-d226-40cb-9f44-b57c-4aa8-a961-98a519447666/moat-login.png" width="300">
<img src="https://github.com/user-attachments/assets/b77799c7-ca98-47cb-b52c-e31ba5135863/moat-admin.png" width="300">
</div>

## Features

*   **Authentication:** User authentication using username/password.
*   **Reverse Proxy:** Proxies requests to backend services after authentication.
*   **Docker Service Discovery:** Automatically discovers and configures services based on Docker labels.
*   **Static Configuration:** Supports static service definitions for non-Docker services.
*   **Single Sign-On (SSO):** Provides a single login point for multiple applications.
*   **Admin UI**: Web interface to manage configuration.

## Prerequisites

*   Python 3.7+
*   Docker (if using Docker service discovery)

## Installation

```bash
git clone https://github.com/kuviman/moat.git
cd moat
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
pip install -r requirements.txt
```

## Configuration

Moat is configured using a `config.yml` file. An example configuration file (`config.example.yml`) is provided.

1.  **Create `config.yml`:** Copy `config.example.yml` to `config.yml` and modify it to suit your environment.
2.  **Set `secret_key`:**  Generate a strong secret key using `openssl rand -hex 32` and set it in `config.yml`. **THIS IS CRUCIAL FOR SECURITY!**
3.  **Configure `moat_base_url`:** This should be the public URL where Moat is accessible (e.g., `https://moat.example.com`).  This is important for correct redirects and cookie settings.
4.  **(Optional) Configure `cookie_domain`:** If your applications are on subdomains of a common domain (e.g., `app1.example.com`, `app2.example.com`), set `cookie_domain` to `.example.com` for SSO to work correctly. If you are NOT using subdomains, leave this as `null`.
5.  **(Optional) Configure static services:** Add entries to the `static_services` list to define services that are not discovered via Docker.

```yaml
listen_host: 0.0.0.0
listen_port: 8000
secret_key: "YOUR_VERY_SECRET_KEY_CHANGE_THIS_NOW_PLEASE" # Generate with: openssl rand -hex 32
access_token_expire_minutes: 60
database_url: "sqlite+aiosqlite:///./moat.db"
moat_base_url: null
cookie_domain: null
docker_monitor_enabled: true
moat_label_prefix: "moat"
static_services:
#  - hostname: "service1.localhost"
#    target_url: "http://127.0.0.1:9001"
```

## Running Moat

1.  **Initialize the database:**

    ```bash
    moat init-db
    ```

2.  **Create an admin user:**

    ```bash
    moat create-user --username admin
    ```

    You will be prompted to enter a password for the admin user.

3.  **Start the Moat server:**

    ```bash
    moat run
    ```

## Usage

Once Moat is running, access the Moat base URL (configured in `config.yml`) in your browser. You will be redirected to the login page. After logging in, you can access your protected applications through the hostnames configured in Moat.

## CLI Commands

Moat provides a command-line interface (CLI) for managing the server.

*   `moat run`: Starts the Moat server.
*   `moat init-db`: Initializes the database.
*   `moat create-user`: Creates a new user.
    *   `--username`:  The username for the new user.
    *   `--admin`: (Optional) Grant admin privileges to the user.
*   `moat add`: Adds a static service entry to the config.
    *   `--public-hostname`: The public hostname for the service.
    *   `--target-url`: The target URL for the service.
*   `moat update`: Updates a static service entry in the config.
    *   `--public-hostname`: The public hostname for the service to update.
    *   `--target-url`: The new target URL for the service.
*   `moat bind`: Creates a static service entry based on a running Docker container.
    *   `--container-name`: The name of the Docker container.
    *   `--public-hostname`: The public hostname to assign to the container.
*   `moat init-config`: Creates a default `config.yml` file.
*   `moat show-config`: Prints the currently loaded config.

## Troubleshooting

* **"Secret key not configured" / "Moat configuration file not found"**: Ensure `config.yml` exists in the working directory and `secret_key` is set. Run `moat init-config`.
* **Redirect loops or incorrect login URL**: Double-check `moat_base_url` in `config.yml`. It must be the public URL of Moat itself.
* **Cookies not working across subdomains**: Verify `cookie_domain` is set correctly (e.g., `.yourdomain.com`).
* **Docker services not appearing**:
   * Ensure `docker_monitor_enabled: true`.
   * Check Moat's logs for Docker connection errors.
   * Verify container labels match `moat_label_prefix` and include `enable`, `hostname`, and `port`.
   * Ensure Moat has access to the Docker socket (`/var/run/docker.sock`).