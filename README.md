<p align="center"><img src="assets\moat.png" height="250" width="250"/></p>

# Moat - Build a moat around your self-hosted apps.

Moat is a lightweight, FastAPI-based security/SSO gateway that provides authentication and reverse proxying capabilities for your web services. It can manage service discovery through Docker labels or static configuration.

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
<img src="https://github.com/user-attachments/assets/917da6b1-d226-40cb-9f44-75e564828f3f" width="46%"></img><img src="https://github.com/user-attachments/assets/cfe96f05-d018-4fe3-bcd6-19eb3788b0ba" width="30%"></img>
</div>

## Features

* Cookie-based authentication for downstream services.
* Reverse proxy for multiple backend applications.
* Dynamic service registration using Docker container labels.
* Static service registration via configuration file.
* Web UI for managing Moat's configuration.
* CLI for user management and configuration tasks.
* Hot-reloading of service configuration (static and Docker-based).

## Prerequisites

* Python 3.8+
* Docker (optional, if using Docker monitor feature)
* An ASGI server like Uvicorn (included in `requirements.txt`)

## Installation

1. **Clone the repository (or download the source):**
    ```bash
    git clone https://github.com/9-5/moat
    cd moat
    ```

2. **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3. **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

Moat uses a `config.yml` file for its settings.

1. **Initialize Configuration:**
    If `config.yml` doesn't exist in the root directory where you'll run Moat, create one using the CLI:
    ```bash
    python -m moat.main init-config
    ```
    This will create a `config.yml` file with default values.

2. **Edit `config.yml`:**
    Open `config.yml` and **critically review and update** the following:

   * `secret_key`: **MUST be changed** to a strong, unique random string. You can generate one with `openssl rand -hex 32`. This key is used for signing access tokens.
   * `moat_base_url`: Set this to the public URL where Moat's own UI and authentication endpoints will be accessed (e.g., `https://auth.yourdomain.com`). This is crucial if Moat itself is behind another reverse proxy or accessed via a tunnel.
   * `cookie_domain`: Configure this for Single Sign-On (SSO) across your services.
       * For subdomains (e.g., `app1.yourdomain.com`, `app2.yourdomain.com`), use a leading dot: `.yourdomain.com`.
       * If all apps are on the same specific hostname as Moat, or if you are not using subdomains for apps, you might use the specific hostname or leave it as `null` (Moat will then use the hostname from the request to its own login page, which might be less predictable in complex setups).
   * `database_url`: Defines the path to the SQLite database. Default is `./moat.db`.
   * `docker_monitor_enabled`: Set to `true` or `false` to enable/disable Docker event monitoring.
   * `moat_label_prefix`: The prefix for Docker labels Moat will look for (e.g., `moat.enable`).
   * `static_services`: Define services that are not managed by Docker. See examples in the generated file.

## Running Moat

1. **Ensure `config.yml` is configured.**

2. **Add an initial admin user:**
    You need at least one user to log in to Moat's admin UI and for services protected by Moat.
    ```bash
    python -m moat.main add-user
    ```
    Follow the prompts to set a username and password.

3. **Run the server:**
    ```bash
    python -m moat.main run
    ```
    By default, it runs on `0.0.0.0:8000`. You can override this with `--host` and `--port` options, or by changing `listen_host` and `listen_port` in `config.yml`.

    For development of Moat itself, you can enable uvicorn's auto-reload:
    ```bash
    python -m moat.main run --reload
    ```

## Usage

### Protecting Services

* **Static Services:**
    Add entries to the `static_services` list in `config.yml`:
    ```yaml
    static_services:
      - hostname: "myapp.yourdomain.com"
        target_url: "http://localhost:3000" # URL of your backend service
      - hostname: "another-app.yourdomain.com"
        target_url: "http://192.168.1.50:8080"
    ```
    Or use the CLI command (this modifies `config.yml`):
    ```bash
    python -m moat.main config:add-static
    ```

* **Docker Dynamic Services:**
    If `docker_monitor_enabled: true`, Moat will automatically detect and proxy services from running Docker containers that have specific labels. The default prefix is `moat`.
    Required labels on the container:
   * `moat.enable="true"`
   * `moat.hostname="service.yourdomain.com"` (The public hostname Moat will listen on)
   * `moat.port="80"` (The internal port the service listens on *inside* the container)
    Optional label:
   * `moat.scheme="http"` (or `https`, default is `http`)

    Example Docker run command:
    ```bash
    docker run -d \
      --label moat.enable="true" \
      --label moat.hostname="myservice.yourdomain.com" \
      --label moat.port="3000" \
      my-service-image
    ```
    Moat will then proxy requests for `myservice.yourdomain.com` to this container on port `3000`.

### Using Cloudflared Tunnels
Use the [cloudflared](assets/cloudflared.md) guide.

### Accessing Services

Once Moat is running and services are configured:
1. Access a protected service via its public hostname (e.g., `http://myapp.yourdomain.com`).
2. If not authenticated, Moat will redirect you to its login page (hosted at `moat_base_url` + `/moat/auth/login`).
3. After successful login, you'll be redirected back to the originally requested service.
4. The authentication cookie will be set for the `cookie_domain` specified in `config.yml`, allowing SSO.

### Admin UI

If you are authenticated and access Moat directly via its `moat_base_url` (e.g., `https://auth.yourdomain.com/`), you will be redirected to the admin configuration page (`/moat/admin/config`). Here you can view and edit the `config.yml` content directly. Changes to `static_services` and Docker monitor settings are hot-reloaded.

## CLI Commands

Moat provides a few CLI commands:

* `python -m moat.main run [--host <host>] [--port <port>] [--reload]`: Runs the server.
* `python -m moat.main init-config [--force]`: Creates a default `config.yml`.
* `python -m moat.main add-user`: Adds a new user to the database.
* `python -m moat.main config:add-static`: Adds a static service entry to `config.yml`.
* `python -m moat.main docker:bind <container_name_or_id> --public-hostname <hostname>`: Adds a running Docker container as a static service to `config.yml` (useful if not using Docker label discovery or for specific overrides).

## Troubleshooting

* **"Secret key not configured" / "Moat configuration file not found"**: Ensure `config.yml` exists in the working directory and `secret_key` is set. Run `moat init-config`.
* **Redirect loops or incorrect login URL**: Double-check `moat_base_url` in `config.yml`. It must be the public URL of Moat itself.
* **Cookies not working across subdomains**: Verify `cookie_domain` is set correctly (e.g., `.yourdomain.com`).
* **Docker services not appearing**:
   * Ensure `docker_monitor_enabled: true`.
   * Check Moat's logs for Docker connection errors.
   * Verify container labels match `moat_label_prefix` and include `enable`, `hostname`, and `port`.
   * Ensure Moat has access to the Docker socket (`/var/run/docker.sock`).
