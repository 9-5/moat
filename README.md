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
<img src="https://github.com/user-attachments/assets/917da6b1-d226-40cb-9f44-b279-9f771487999c/moat-admin-config.png" width="800" />
<p>Admin configuration UI</p>
</div>
<div align="center">
<img src="https://github.com/user-attachments/assets/917da6b1-d226-40cb-9f44-b279-9f771487999c/moat-login.png" width="800" />
<p>Login page</p>
</div>

## Features

*   **Centralized Authentication:** Protect multiple applications with a single login.
*   **Reverse Proxy:** Routes traffic to your applications after successful authentication.
*   **Docker Integration:** Automatically discover and proxy Docker containers based on labels.
*   **Static Configuration:** Define services manually for non-Docker applications.
*   **Admin UI:** Web interface for managing configuration.
*   **Secure Cookie Handling:** Configurable cookie domain and security settings.
*   **Cloudflare Tunnel support**: Detailed guide for integration with Cloudflare Tunnels.

## Prerequisites

*   Python 3.7+
*   Docker (optional, for Docker integration)

## Installation

1.  Clone the repository:

    ```bash
    git clone https://github.com/jordanbaird/moat.git
    cd moat
    ```
2.  Create a virtual environment:

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
3.  Install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

## Configuration

1.  Initialize the configuration file:

    ```bash
    moat init-config
    ```
2.  Edit `config.yml` to set your desired settings.  Pay CLOSE attention to `secret_key`, `moat_base_url`, and `cookie_domain`.

## Running Moat

```bash
python3 -m moat.main run
```

## Usage

Once Moat is running, access it through your configured `moat_base_url`.  You will be prompted to create an initial user.  After logging in, you can access your proxied applications through their configured hostnames.

## CLI Commands

*   `moat init-config`: Creates a default `config.yml` file.
*   `moat run`: Starts the Moat server.
*   `moat add-user <username>`: Creates a new user.  The command will prompt you for a password.
*   `moat add-static-service <public_hostname> <target_url>`: Manually configures a reverse proxy entry.
*   `moat bind-static-service <public_hostname> <container_name>`: Automatically configures a reverse proxy entry based on a running Docker container.

## Troubleshooting

* **"Secret key not configured" / "Moat configuration file not found"**: Ensure `config.yml` exists in the working directory and `secret_key` is set. Run `moat init-config`.
* **Redirect loops or incorrect login URL**: Double-check `moat_base_url` in `config.yml`. It must be the public URL of Moat itself.
* **Cookies not working across subdomains**: Verify `cookie_domain` is set correctly (e.g., `.yourdomain.com`).
* **Docker services not appearing**:
   * Ensure `docker_monitor_enabled: true`.
   * Check Moat's logs for Docker connection errors.
   * Verify container labels match `moat_label_prefix` and include `enable`, `hostname`, and `port`.
   * Ensure Moat has access to the Docker socket (`/var/run/docker.sock`).