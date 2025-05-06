# Setting Up Moat with Cloudflared (Cloudflare Tunnels)

**Conceptual Overview:**

1.  **Moat:** Runs on your local server (or inside a Docker container on that server), listening on a local port (e.g., `localhost:8000`). It handles authentication and reverse proxies requests to your backend services.
2.  **Backend Services:** These are your actual applications, running locally (e.g., `localhost:3001`, or as Docker containers like `http://my-app-container:80`). Moat needs to be able to reach these on the local network.
3.  **`cloudflared`:** A small daemon from Cloudflare that runs on the same server as Moat. It creates a secure, outbound-only connection to Cloudflare's edge network.
4.  **Cloudflare's Edge:** When a user accesses your public hostname, Cloudflare's edge network forwards the request to your `cloudflared` daemon.

**Configuration Steps:**

1.  **Install and Configure `cloudflared`:** Follow Cloudflare's official documentation to install `cloudflared` on your server.
2.  **Create a Tunnel:** Use `cloudflared tunnel create <tunnel-name>` to create a new tunnel.
3.  **Create DNS Records:** Use `cloudflared tunnel route dns <tunnel-name> <your.hostname.com>` to create DNS records that point your desired hostnames to the Cloudflare tunnel. This is what makes your services publicly accessible.
4.  **Configure the Tunnel to Proxy to Moat:**  This is the crucial part. You need to tell `cloudflared` to forward requests to Moat. The `cloudflared` config file (usually `~/.cloudflared/config.yml`) should include:

```yaml
tunnel: <your-tunnel-id>
credentials-file: /root/.cloudflared/<your-tunnel-id>.json

ingress:
  - hostname: moat.yourdomain.com # Your Moat hostname
    service: http://localhost:8000  # Moat's local address
  - hostname: app1.yourdomain.com  # Example app 1
    service: http://localhost:3001
  - hostname: app2.yourdomain.com  # Example app 2
    service: http://my-docker-app:80 # Accessing a Docker container
  - service: http_status:404
```

**Important Considerations:**

*   **Moat's `config.yml`:**
    *   **`moat_base_url`:**  **MUST** be set to the public URL where Moat is accessible through Cloudflare Tunnel (e.g., `https://moat.yourdomain.com`). This is essential for correct redirects after login.
    *   **`cookie_domain`:** Should be set to your domain (e.g., `.yourdomain.com`) for SSO to work correctly across subdomains.
*   **Docker:** If your applications are running in Docker containers, ensure Moat can resolve their hostnames (e.g., using Docker Compose's network or setting up DNS).

**Troubleshooting:**

*   **General Connectivity Issues:**
    *   Double-check that `cloudflared` is running and correctly proxying.
    *   Verify that Moat is running and accessible on its local port (e.g., `http://localhost:8000`) from the server where `cloudflared` is running. This is crucial before concerning yourself with external proxying.
*   **Redirect Loops:**
    *   Verify `moat_base_url` in Moat's `config.yml` is **exactly** `https://moat.yourdomain.com` (or your equivalent).
    *   Check `X-Forwarded-Proto` and `X-Forwarded-Host` headers. Cloudflare tunnels generally set these correctly.
*   **Cookie Issues / Not Staying Logged In:**
    *   Ensure `cookie_domain` in Moat's `config.yml` is correct (e.g., `.yourdomain.com`).
    *   Check browser developer tools to see if cookies are being set for the correct domain.
*   **DNS Issues:** Ensure your DNS records created via `cloudflared tunnel route dns` have propagated. Use `dig` or `nslookup` for your public hostnames.

This detailed guide should help you get Moat up and running securely with Cloudflare Tunnel!