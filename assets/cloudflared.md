# Setting Up Moat with Cloudflared (Cloudflare Tunnels)

**Conceptual Overview:**

1.  **Moat:** Runs on your local server (or inside a Docker container on that server), listening on a local port (e.g., `localhost:8000`). It handles authentication and reverse proxies requests to your backend services.
2.  **Backend Services:** These are your actual applications, running locally (e.g., `localhost:3001`, or as Docker containers like `http://my-app-container:80`). Moat needs to be able to reach these on the local network.
3.  **`cloudflared`:** A small daemon from Cloudflare that runs on the same server as Moat. It creates a secure, outbound-only connection to Cloudflare's edge network.
4.  **Cloudflare's Edge:** When a user accesses your public hostname (e.g., `app.yourdomain.com`), Cloudflare's edge network receives the request.
5.  **The Tunnel:** The `cloudflared` daemon creates an outbound-only tunnel to Cloudflare's edge, allowing traffic to flow to Moat without opening any inbound ports on your server.
6.  **Moat's Role:** Moat authenticates the user (if required) and then reverse proxies the request to the appropriate backend service.

**Diagram:**

```
User --> Cloudflare Edge --> cloudflared (Tunnel) --> Moat --> Backend Service
```

**Steps:**

1.  **Install and Configure `cloudflared`:** Follow Cloudflare's official documentation to install `cloudflared` on your server.
2.  **Create a Tunnel:** Use `cloudflared tunnel create <tunnel-name>` to create a new tunnel.
3.  **Authenticate `cloudflared`:** Use `cloudflared tunnel login` to authenticate the `cloudflared` daemon with your Cloudflare account.
4.  **Create DNS Records:** Use `cloudflared tunnel route dns <tunnel-name> <hostname>` to create DNS records in Cloudflare that point to your tunnel.  For example:
    ```bash
    cloudflared tunnel route dns my-tunnel moat.yourdomain.com
    cloudflared tunnel route dns my-tunnel app.yourdomain.com
    cloudflared tunnel route dns my-tunnel anotherapp.yourdomain.com
    ```
    This will route traffic for `moat.yourdomain.com`, `app.yourdomain.com`, and `anotherapp.yourdomain.com` through the tunnel.  `moat.yourdomain.com` should point to your Moat instance.
5.  **Create a Configuration File:** Create a `config.yml` file for `cloudflared` (typically located at `~/.cloudflared/config.yml`).  This file specifies how `cloudflared` should route traffic.  A basic example:

    ```yaml
    tunnel: <your-tunnel-id>
    credentials-file: /root/.cloudflared/<your-tunnel-id>.json

    ingress:
      - hostname: moat.yourdomain.com
        service: http://localhost:8000  # Moat's local address

      - hostname: app.yourdomain.com
        service: http://localhost:3001  # Your backend application

      - hostname: anotherapp.yourdomain.com
        service: http://localhost:3002 # Another backend application

      - service: http_status:404
    ```

    *   Replace `<your-tunnel-id>` with the actual tunnel ID.
    *   Adjust the `hostname` and `service` values to match your setup.  `localhost:8000` assumes Moat is running on the same server as `cloudflared` and listening on port 8000.  The other services point to your backend applications.
    *   The final `service: http_status:404` entry is a catch-all that returns a 404 error for any unmatched hostnames.

6.  **Run the Tunnel:** Start the tunnel using `cloudflared tunnel run <tunnel-name>`.
7.  **Configure Moat:**
    *   Set `moat_base_url` in Moat's `config.yml` to `https://moat.yourdomain.com`.  This is **critical** for correct redirects and cookie handling.
    *   Set `cookie_domain` in Moat's `config.yml` to `.yourdomain.com` to ensure cookies work correctly across subdomains.

**Important Considerations:**

*   **HTTPS:** Cloudflare tunnels automatically handle HTTPS.  You do **not** need to configure HTTPS certificates on your local server for traffic coming through the tunnel.
*   **Security:** Cloudflare tunnels are outbound-only, meaning no inbound ports need to be opened on your server, significantly improving security.
*   **Moat's `moat_base_url`:** This setting is absolutely crucial.  It tells Moat the public URL it is accessible at.  If this is incorrect, you will experience redirect loops or other issues.
*   **Cookie Domain:** The `cookie_domain` setting in Moat's `config.yml` must be set correctly for SSO to work across subdomains.

**Troubleshooting:**

*   **Cloudflared Connection Issues:** Check the `cloudflared` logs for errors.  Ensure the tunnel is running and properly authenticated.
*   **Moat Not Accessible:** Ensure the `cloudflared` configuration is routing traffic to Moat's local address (e.g., `localhost:8000`).
*   **Redirect Loops:**
    *   Verify `moat_base_url` in Moat's `config.yml` is **exactly** `https://moat.yourdomain.com` (or your equivalent).
    *   Check `X-Forwarded-Proto` and `X-Forwarded-Host` headers. Cloudflare tunnels generally set these correctly.
*   **Cookie Issues / Not Staying Logged In:**
    *   Ensure `cookie_domain` in Moat's `config.yml` is correct (e.g., `.yourdomain.com`).
    *   Check browser developer tools to see if cookies are being set for the correct domain.
*   **DNS Issues:** Ensure your DNS records created via `cloudflared tunnel route dns` have propagated. Use `dig` or `nslookup` for your public hostnames.

This detailed guide should help you get Moat up and running securely with Cloudflare Tunnel!