# Setting Up Moat with Cloudflared (Cloudflare Tunnels)

**Conceptual Overview:**

1.  **Moat:** Runs on your local server (or inside a Docker container on that server), listening on a local port (e.g., `localhost:8000`). It handles authentication and reverse proxies requests to your backend services.
2.  **Backend Services:** These are your actual applications, running locally (e.g., `localhost:3001`, or as Docker containers like `http://my-app-container:80`). Moat needs to be able to reach these on the local network.
3.  **`cloudflared`:** A small daemon from Cloudflare that runs on the same server as Moat. It creates a secure, outbound-only connection to Cloudflare's edge network.
4.  **Cloudflare's Edge:** When a user accesses your publicly accessible domain (`yourdomain.com`) is accessed, Cloudflare's edge network routes the traffic through the tunnel to `cloudflared`. `cloudflared` then forwards the request to Moat. Moat authenticates the user (if necessary) and proxies the request to the appropriate backend service.

**Configuration Steps:**

1.  **Install `cloudflared`:** Follow Cloudflare's official instructions for installing `cloudflared` on your server.
2.  **Authenticate `cloudflared`:** Run `cloudflared tunnel login` and select your Cloudflare account.
3.  **Create a Tunnel:**
    ```bash
    cloudflared tunnel create moat-tunnel
    ```
    This will give you a Tunnel ID (a UUID).
4.  **Create a Configuration File:** Create a `config.yml` file for `cloudflared` (e.g., `/etc/cloudflared/config.yml`).  Replace the Tunnel ID with your actual Tunnel ID.  This example assumes Moat is running on `localhost:8000`.  Adjust the `service` URL to match your Moat instance's address.
    ```yaml
    tunnel: <YOUR_TUNNEL_ID>
    credentials-file: /root/.cloudflared/<YOUR_TUNNEL_ID>.json

    ingress:
      - hostname: moat.yourdomain.com
        service: http://localhost:8000
      - service: http_status:404
    ```
5.  **Create DNS Records:** Use `cloudflared tunnel route dns` to create DNS records in Cloudflare that point your desired hostnames (e.g., `moat.yourdomain.com`) to the tunnel.
    ```bash
    cloudflared tunnel route dns moat-tunnel moat.yourdomain.com
    ```
6.  **Run the Tunnel:**
    ```bash
    cloudflared tunnel run moat-tunnel
    ```
    Or, for persistent execution:
    ```bash
    cloudflared service install
    cloudflared tunnel run
    ```

**Moat Configuration (`config.yml`):**

*   Set `moat_base_url` to your public-facing Cloudflare Tunnel URL (e.g., `https://moat.yourdomain.com`).  This is **critical** for correct redirects after login.
*   Set `cookie_domain` to your domain (e.g., `.yourdomain.com`) for proper cookie handling across subdomains.

```yaml
listen_host: "0.0.0.0"
listen_port: 8000
secret_key: "YOUR_VERY_SECRET_KEY_CHANGE_THIS_NOW_PLEASE"
access_token_expire_minutes: 60
database_url: "sqlite+aiosqlite:///./moat.db"
moat_base_url: "https://moat.yourdomain.com"
cookie_domain: ".yourdomain.com"
docker_monitor_enabled: true
moat_label_prefix: "moat"
static_services: []
```

**Important Considerations:**

*   **HTTPS:** Cloudflare Tunnel provides HTTPS encryption between Cloudflare's edge and your server. Moat itself can run on HTTP internally (`http://localhost:8000`), but `moat_base_url` **must** be the HTTPS URL served by Cloudflare.
*   **DNS Propagation:** Allow time for DNS records created via `cloudflared tunnel route dns` to propagate.
*   **Security:** Cloudflare Tunnel provides an additional layer of security by ensuring all traffic to your server goes through Cloudflare's network.

**Troubleshooting:**

*   **Cloudflared Connection Issues:** Check `cloudflared` logs for connection errors. Ensure `cloudflared` is properly authenticated and the tunnel is running.
*   **Moat Not Accessible:** Verify the `cloudflared` configuration, especially the `service` URL. Double-check that Moat is running and accessible on the specified local port.
*   **Reverse Proxying:** Ensure Moat's `static_services` or Docker labels are correctly configured for reverse proxying.
*   **Redirect Loops:**
    *   Verify `moat_base_url` in Moat's `config.yml` is **exactly** `https://moat.yourdomain.com` (or your equivalent).
    *   Check `X-Forwarded-Proto` and `X-Forwarded-Host` headers. Cloudflare tunnels generally set these correctly.
*   **Cookie Issues / Not Staying Logged In:**
    *   Ensure `cookie_domain` in Moat's `config.yml` is correct (e.g., `.yourdomain.com`).
    *   Check browser developer tools to see if cookies are being set for the correct domain.
*   **DNS Issues:** Ensure your DNS records created via `cloudflared tunnel route dns` have propagated. Use `dig` or `nslookup` for your public hostnames.

This detailed guide should help you get Moat up and running securely with Cloudflare Tunnel!