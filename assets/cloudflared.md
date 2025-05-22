# Setting Up Moat with Cloudflared (Cloudflare Tunnels)

**Conceptual Overview:**

1.  **Moat:** Runs on your local server (or inside a Docker container on that server), listening on a local port (e.g., `localhost:8000`). It handles authentication and reverse proxies requests to your backend services.
2.  **Backend Services:** These are your actual applications, running locally (e.g., `localhost:3001`, or as Docker containers like `http://my-app-container:80`). Moat needs to be able to reach these on the local network.
3.  **`cloudflared`:** A small daemon from Cloudflare that runs on the same server as Moat. It creates a secure, outbound-only connection to Cloudflare's edge network.
4.  **Cloudflare's Edge:** When a user accesses your publicly accessible domain (e.g., `myapp.yourdomain.com`), Cloudflare's edge network receives the request.
5.  **The Tunnel:** The `cloudflared` daemon establishes an encrypted tunnel to Cloudflare's edge.
6.  **Proxying:** Cloudflare then proxies the incoming request **through the tunnel** to your `cloudflared` instance.
7.  **Moat's Role:** `cloudflared` forwards the request to Moat. Moat authenticates the user (or redirects to the login page), and if successful, proxies the request to your backend service.
8.  **Response:** The response follows the reverse path: Backend Service -> Moat -> `cloudflared` -> Cloudflare Edge -> User.

**Why Cloudflare Tunnel?**

*   **Security:** No open inbound ports on your server. The connection is outbound-only, reducing the attack surface.
*   **DDOS Protection:** Cloudflare provides DDOS protection and other security features.
*   **SSL/TLS:** Cloudflare handles SSL/TLS termination, so you don't need to manage certificates on your server (though you *can* use "Full (strict)" mode for end-to-end encryption).
*   **Global Network:** Cloudflare's global network provides faster and more reliable access to your services.

**Steps:**

1.  **Install `cloudflared`:** Follow Cloudflare's official documentation to install `cloudflared` on your server.
2.  **Authenticate `cloudflared`:** Authenticate `cloudflared` with your Cloudflare account. This typically involves logging in through a browser and selecting your domain.
3.  **Create a Tunnel:** Create a tunnel using `cloudflared tunnel create <tunnel-name>`.
4.  **Configure the Tunnel:** Create a `config.yml` file for `cloudflared` (usually in `~/.cloudflared/config.yml`).  This file defines how `cloudflared` will route traffic.  Here's a basic example:

    ```yaml
    tunnel: <your-tunnel-id>
    credentials-file: /root/.cloudflared/<your-tunnel-id>.json

    ingress:
      - hostname: moat.yourdomain.com # The public hostname for Moat itself
        service: http://localhost:8000  # Where Moat is running
      - hostname: app1.yourdomain.com  # Example app
        service: http://localhost:3001  # Where app1 is running
      - service: http_status:404 # Catch-all
    ```

    **Important Considerations:**

    *   Replace `<your-tunnel-id>` with the actual Tunnel ID.
    *   Ensure the `hostname` values match the DNS records you'll create in Cloudflare.
    *   The `service` entries point to the **internal** addresses of your services.  Moat must be able to reach these addresses.
    *   Moat itself needs a `hostname` entry in the `cloudflared` config so that Cloudflare knows where to route traffic for Moat's login page and admin UI.
5.  **Create DNS Records:** Use the `cloudflared tunnel route dns` command to create DNS records in Cloudflare that point your hostnames to the tunnel. For example:

    ```bash
    cloudflared tunnel route dns <tunnel-name> moat.yourdomain.com
    cloudflared tunnel route dns <tunnel-name> app1.yourdomain.com
    ```

    Alternatively, you can manually create CNAME records in the Cloudflare dashboard.  The target should be the tunnel's assigned `cfargotunnel.com` address.
6.  **Run the Tunnel:** Start the tunnel using `cloudflared tunnel run <tunnel-name>`.  You can run this in the background using a service manager like `systemd`.
7.  **Configure Moat:**  In Moat's `config.yml`:

    *   Set `moat_base_url` to the **public hostname** you're using for Moat in Cloudflare (e.g., `https://moat.yourdomain.com`).  This is crucial for redirects to work correctly.
    *   Set `cookie_domain` to your domain (e.g., `.yourdomain.com`) so cookies work across subdomains.
8.  **Access your Services:**  Access your services through the hostnames you configured in Cloudflare.  You should be redirected to Moat for authentication.

**Example `moat.config.yml`:**

```yaml
listen_host: 0.0.0.0
listen_port: 8000
secret_key: "YOUR_VERY_SECRET_KEY_CHANGE_THIS_NOW_PLEASE"
access_token_expire_minutes: 60
database_url: "sqlite+aiosqlite:///./moat.db"
moat_base_url: https://moat.yourdomain.com  # MUST match Cloudflare tunnel hostname
cookie_domain: .yourdomain.com           # For SSO across subdomains
docker_monitor_enabled: false
moat_label_prefix: "moat"
static_services:
  - hostname: app1.yourdomain.com       # MUST match Cloudflare tunnel hostname
    target_url: http://localhost:3001  # Internal address of the app
```

**Troubleshooting with Cloudflare Tunnel and Moat:**

*   **Ensure `cloudflared` is Running:** Verify that the `cloudflared` tunnel is running without errors. Check its logs.
*   **DNS Propagation:**  It can take a few minutes for DNS records to propagate after creating them in Cloudflare.
*   **SSL/TLS Configuration:**  In Cloudflare, the "SSL/TLS encryption mode" setting should generally be set to "Full" or "Full (strict)".  "Flexible" mode can cause issues with HTTPS proxying.
*   **`cloudflared` config.yml Syntax:** Double-check the syntax of your `cloudflared` config.yml file.  YAML is sensitive to indentation.  Use a YAML validator.
*   **Moat Base URL:** `moat_base_url` in `moat.config.yml` **must** be the public-facing URL served by Cloudflare proxying.
*   **Redirect Loops:**
    *   Verify `moat_base_url` in Moat's `config.yml` is **exactly** `https://moat.yourdomain.com` (or your equivalent).
    *   Check `X-Forwarded-Proto` and `X-Forwarded-Host` headers. Cloudflare tunnels generally set these correctly.
*   **Cookie Issues / Not Staying Logged In:**
    *   Ensure `cookie_domain` in Moat's `config.yml` is correct (e.g., `.yourdomain.com`).
    *   Check browser developer tools to see if cookies are being set for the correct domain.
*   **DNS Issues:** Ensure your DNS records created via `cloudflared tunnel route dns` have propagated. Use `dig` or `nslookup` for your public hostnames.

This detailed guide should help you get Moat up and running securely with Cloudflare Tunnel!