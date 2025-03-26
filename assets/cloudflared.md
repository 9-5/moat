# Setting Up Moat with Cloudflared (Cloudflare Tunnels)

**Conceptual Overview:**

1.  **Moat:** Runs on your local server (or inside a Docker container on that server), listening on a local port (e.g., `localhost:8000`). It handles authentication and reverse proxies requests to your backend services.
2.  **Backend Services:** These are your actual applications, running locally (e.g., `localhost:3001`, or as Docker containers like `http://my-app-container:80`). Moat needs to be able to reach these on the local network.
3.  **`cloudflared`:** A small daemon from Cloudflare that runs on the same server as Moat. It creates a secure, outbound-only connection to Cloudflare's edge network.
4.  **Cloudflare's Edge:** When a user accesses your public services, Cloudflare forwards the request through the tunnel to `cloudflared`, which then sends the request to Moat.

**Configuration Steps:**

1.  **Install `cloudflared`:** Follow Cloudflare's official documentation to install `cloudflared` on your server.
2.  **Authenticate `cloudflared` with your Cloudflare account:** Use `cloudflared login`.
3.  **Create a Tunnel:** `cloudflared tunnel create <tunnel-name>`. This will give you a Tunnel ID.
4.  **Create a Configuration File:** Create a `config.yml` file for `cloudflared` (e.g., in `/etc/cloudflared/config.yml`). A minimal example:

```yaml
tunnel: <your-tunnel-id>
credentials-file: /root/.cloudflared/<your-tunnel-id>.json
ingress:
  - hostname: moat.yourdomain.com # Public hostname for Moat
    service: http://localhost:8000  # Moat's local address
  - hostname: app1.yourdomain.com  # Public hostname for App 1
    service: http://localhost:3001  # App 1's local address
  - hostname: app2.yourdomain.com
    service: http://my-app-container:80 #App 2 running as Docker container
  - service: http_status:404 # Catch-all for unmatched requests
```

5.  **Create DNS Records:** Use `cloudflared tunnel route dns <tunnel-name> <hostname> <record-type>`. Example:

```bash
cloudflared tunnel route dns my-tunnel moat.yourdomain.com A
cloudflared tunnel route dns my-tunnel app1.yourdomain.com CNAME
cloudflared tunnel route dns my-tunnel app2.yourdomain.com CNAME
```

6.  **Run the Tunnel:** `cloudflared tunnel run <tunnel-name>`
7.  **Configure Moat:**
    *   Set `moat_base_url` in Moat's `config.yml` to the **public** hostname you're using with Cloudflare (e.g., `https://moat.yourdomain.com`).  This is crucial for correct redirects after login.
    *   If your apps are on subdomains, set the `cookie_domain` in Moat's `config.yml` (e.g. `.yourdomain.com`).
8.  **Important Considerations:**
    *   **TLS:** Cloudflare tunnels handle TLS termination.  Moat itself only needs to serve HTTP on the local network.
    *   **Origin CA:** Consider using Cloudflare Origin CA certificates for enhanced security between Cloudflare and your origin server.

**Troubleshooting:**

*   **Cloudflare Status Page:** Check Cloudflare's status page for any known issues affecting tunneling or proxying.
*   **Redirect Loops:**
    *   Verify `moat_base_url` in Moat's `config.yml` is **exactly** `https://moat.yourdomain.com` (or your equivalent).
    *   Check `X-Forwarded-Proto` and `X-Forwarded-Host` headers. Cloudflare tunnels generally set these correctly.
*   **Cookie Issues / Not Staying Logged In:**
    *   Ensure `cookie_domain` in Moat's `config.yml` is correct (e.g., `.yourdomain.com`).
    *   Check browser developer tools to see if cookies are being set for the correct domain.
*   **DNS Issues:** Ensure your DNS records created via `cloudflared tunnel route dns` have propagated. Use `dig` or `nslookup` for your public hostnames.

This detailed guide should help you get Moat up and running securely with Cloudflare Tunnel!