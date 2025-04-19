# Setting Up Moat with Cloudflared (Cloudflare Tunnels)

**Conceptual Overview:**

1.  **Moat:** Runs on your local server (or inside a Docker container on that server), listening on a local port (e.g., `localhost:8000`). It handles authentication and reverse proxies requests to your backend services.
2.  **Backend Services:** These are your actual applications, running locally (e.g., `localhost:3001`, or as Docker containers like `http://my-app-container:80`). Moat needs to be able to reach these on the local network.
3.  **`cloudflared`:** A small daemon from Cloudflare that runs on the same server as Moat. It creates a secure, outbound-only connection to Cloudflare's edge network.
4.  **Cloudflare's Edge:** When a user accesses your public website, the request hits Cloudflare's edge network first. Cloudflare then forwards it through the secure tunnel established by `cloudflared` to your Moat instance.

**Configuration Steps:**

1.  **Install and Authenticate `cloudflared`:**

    *   Follow Cloudflare's official documentation to install `cloudflared` on your server:  [https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/)
    *   Authenticate `cloudflared` with your Cloudflare account: `cloudflared login`

2.  **Create a Cloudflare Tunnel:**

    *   `cloudflared tunnel create <tunnel-name>`  (Choose a descriptive tunnel name, e.g., `moat-tunnel`)
    *   This will generate a tunnel ID and a credentials file (`.json`) in the `~/.cloudflared/` directory.

3.  **Configure DNS Records:**

    *   You'll need to point DNS records in Cloudflare to your tunnel.  Use the `cloudflared tunnel route dns` command.  For example, to route `moat.yourdomain.com` to your Moat instance:
        ```bash
        cloudflared tunnel route dns <tunnel-name> moat.yourdomain.com
        ```
        Replace `<tunnel-name>` with the name you chose in step 2.

4.  **Create a Configuration File for `cloudflared`:**

    *   Create a `config.yml` file (e.g., in `/etc/cloudflared/config.yml`) for `cloudflared` to specify how to route traffic to Moat.  Here's a basic example:

        ```yaml
        tunnel: <tunnel-id>  # Replace with your tunnel ID
        credentials-file: /root/.cloudflared/<tunnel-id>.json # Adjust path if needed
        ingress:
          - hostname: moat.yourdomain.com
            service: http://localhost:8000  # Moat's local address and port
          - service: http_status:404 # Default to 404 if no route matches
        ```
        **Important:**  The `hostname` in the `cloudflared` config **must** match the hostname you used in the `cloudflared tunnel route dns` command.  The `service` should point to the **local** address where Moat is running (e.g., `http://localhost:8000`).

5.  **Run the Tunnel:**

    *   Start the Cloudflare tunnel:
        ```bash
        cloudflared tunnel run <tunnel-name>
        ```
        Or, using the config file:
        ```bash
        cloudflared --config /etc/cloudflared/config.yml tunnel run
        ```
        Consider setting this up as a systemd service for automatic restarting.

6.  **Configure Moat:**

    *   In Moat's `config.yml`:
        *   Set `moat_base_url` to the **public hostname** you configured in Cloudflare (e.g., `https://moat.yourdomain.com`).  This is crucial for correct redirects after login.
        *   Set `cookie_domain` to your domain (e.g., `.yourdomain.com`).

**Example Scenario:**

Let's say you want to host Moat and a backend application (`my-app`) behind a Cloudflare Tunnel.

*   **Moat:** Runs on `localhost:8000`
*   **`my-app`:**  Runs on `localhost:3001`
*   **Cloudflare Tunnel:**  You've created a tunnel named `my-tunnel`.
*   **DNS Records:**
    *   `moat.yourdomain.com` points to the tunnel.
    *   `app.yourdomain.com` points to the tunnel.

**`cloudflared` config.yml:**

```yaml
tunnel: <your-tunnel-id>
credentials-file: /root/.cloudflared/<your-tunnel-id>.json
ingress:
  - hostname: moat.yourdomain.com
    service: http://localhost:8000
  - hostname: app.yourdomain.com
    service: http://localhost:3001
  - service: http_status:404
```

**Moat `config.yml`:**

```yaml
listen_host: "0.0.0.0"
listen_port: 8000
secret_key: "YOUR_VERY_SECRET_KEY_CHANGE_THIS_NOW_PLEASE"
database_url: "sqlite+aiosqlite:///./moat.db"
moat_base_url: https://moat.yourdomain.com
cookie_domain: .yourdomain.com
docker_monitor_enabled: false
static_services: []
```

**Important Considerations:**

*   **Security:** Cloudflare Tunnel creates outbound-only connections, reducing your server's attack surface.
*   **HTTPS:** Ensure you are using HTTPS in Cloudflare for your domain. Cloudflare handles the SSL termination.
*   **Subdomains:**  Using subdomains (like `moat.yourdomain.com`, `app1.yourdomain.com`) is generally the best practice for routing different services through the tunnel.

**Troubleshooting:**

*   **Connection Refused:** Double-check that Moat is running and accessible on the local address specified in the `cloudflared` config (e.g., `http://localhost:8000`).
*   **"Bad Gateway" errors:** Usually indicate a problem with the tunnel configuration or that the backend service is not reachable.
*   **520/521/522 Errors:** These are Cloudflare-specific errors that indicate problems with the connection between Cloudflare and your origin server (Moat). Check Cloudflare's documentation for troubleshooting these.
*   **Redirect Loops:**
    *   Verify `moat_base_url` in Moat's `config.yml` is **exactly** `https://moat.yourdomain.com` (or your equivalent).
    *   Check `X-Forwarded-Proto` and `X-Forwarded-Host` headers. Cloudflare tunnels generally set these correctly.
*   **Cookie Issues / Not Staying Logged In:**
    *   Ensure `cookie_domain` in Moat's `config.yml` is correct (e.g., `.yourdomain.com`).
    *   Check browser developer tools to see if cookies are being set for the correct domain.
*   **DNS Issues:** Ensure your DNS records created via `cloudflared tunnel route dns` have propagated. Use `dig` or `nslookup` for your public hostnames.

This detailed guide should help you get Moat up and running securely with Cloudflare Tunnel!