# Setting Up Moat with Cloudflared (Cloudflare Tunnels)

**Conceptual Overview:**

1.  **Moat:** Runs on your local server (or inside a Docker container on that server), listening on a local port (e.g., `localhost:8000`). It handles authentication and reverse proxies requests to your backend services.
2.  **Backend Services:** These are your actual applications, running locally (e.g., `localhost:3001`, or as Docker containers like `http://my-app-container:80`). Moat needs to be able to reach these on the local network.
3.  **`cloudflared`:** A small daemon from Cloudflare that runs on the same server as Moat. It creates a secure, outbound-only connection to Cloudflare's edge network.
4.  **Cloudflare's Edge:** When a user accesses your public services via Cloudflare, Cloudflare routes the traffic to your server through the secure tunnel created by `cloudflared`.

**Configuration Steps:**

1.  **Install and Configure `cloudflared`:** Follow the official Cloudflare Tunnel documentation to install `cloudflared` on your server and create a tunnel: [https://developers.cloudflare.com/cloudflare-one/connections/tunnel/](https://developers.cloudflare.com/cloudflare-one/connections/tunnel/)

2.  **Create DNS Records:** Use the `cloudflared tunnel route dns` command to create DNS records in Cloudflare that point your desired hostnames to your tunnel.  For example:

    ```bash
    cloudflared tunnel route dns your-tunnel-name app1.yourdomain.com
    cloudflared tunnel route dns your-tunnel-name app2.yourdomain.com
    ```

3.  **Configure Moat:**

    *   **`config.yml`:**
        *   Set `moat_base_url` to the public URL of your Moat instance (e.g., `https://moat.yourdomain.com`).  This is crucial for redirects to work correctly.
        *   Set `cookie_domain` to your domain (e.g., `.yourdomain.com`) to enable SSO across subdomains.
    *   **Ensure Moat can reach your backend services:** If your backend services are running on the same server as Moat, you can use `localhost` or the container name (if using Docker). If they are on different servers, ensure Moat can access them via their internal network addresses.

**Example Scenario:**

Let's say you have two applications:

*   `app1`: Running locally on your server at `localhost:3001`.
*   `app2`: Running in a Docker container named `my-app-container` and exposing port 80.

You want to access these applications via:

*   `https://app1.yourdomain.com`
*   `https://app2.yourdomain.com`

**Configuration:**

Your `cloudflared` configuration should have rules that forward traffic for `app1.yourdomain.com` and `app2.yourdomain.com` to your local Moat instance (e.g., `localhost:8000`). This usually involves creating a `config.yml` file for `cloudflared` and then running the tunnel. See Cloudflare's documentation.

Your Moat `config.yml` should look something like this:

```yaml
listen_host: 0.0.0.0
listen_port: 8000
secret_key: ...
access_token_expire_minutes: 60
database_url: sqlite+aiosqlite:///./moat.db
moat_base_url: https://moat.yourdomain.com  # IMPORTANT: Public URL of Moat!
cookie_domain: .yourdomain.com # IMPORTANT: For SSO
docker_monitor_enabled: true
moat_label_prefix: moat
static_services:
  - hostname: app1.yourdomain.com
    target_url: http://localhost:3001
```

And that your Docker container for `app2` has labels like:

```yaml
labels:
  moat.enable: "true"
  moat.hostname: "app2.yourdomain.com"
  moat.port: "80"
```

With this configuration, when a user accesses `https://app1.yourdomain.com`, Cloudflare will route the request to your server, `cloudflared` will forward it to Moat, Moat will authenticate the user, and then proxy the request to `localhost:3001`. The same process will occur for `https://app2.yourdomain.com`, but the request will be proxied to the `my-app-container` Docker container.  Unauthenticated users will be redirected to the Moat login page.

**Troubleshooting:**

*   **Cloudflared Connection Issues:**  Check `cloudflared` logs for connection errors.  Ensure your tunnel is active and correctly configured in Cloudflare.
*   **Moat Not Reachable:** Verify that `cloudflared` is correctly forwarding traffic to Moat's listening address (e.g., `localhost:8000`).  Use `curl` from the server running `cloudflared` to test the connection: `curl http://localhost:8000`.  You should see Moat's login page or a reverse proxying error.
*   **Reverse Proxying Problems:**
    *   Ensure that `moat_base_url` is set to your **public** `moat.yourdomain.com` and **not** a local address like `localhost:8000`.  This is essential for correct redirect behavior after authentication.
    *   Double-check that Moat can access your backend services.  Use `curl` from the Moat server to test the connection to your backend service's target URL.
*   **Redirect Loops:**
    *   Verify `moat_base_url` in Moat's `config.yml` is **exactly** `https://moat.yourdomain.com` (or your equivalent).
    *   Check `X-Forwarded-Proto` and `X-Forwarded-Host` headers. Cloudflare tunnels generally set these correctly.
*   **Cookie Issues / Not Staying Logged In:**
    *   Ensure `cookie_domain` in Moat's `config.yml` is correct (e.g., `.yourdomain.com`).
    *   Check browser developer tools to see if cookies are being set for the correct domain.
*   **DNS Issues:** Ensure your DNS records created via `cloudflared tunnel route dns` have propagated. Use `dig` or `nslookup` for your public hostnames.

This detailed guide should help you get Moat up and running securely with Cloudflare Tunnel!