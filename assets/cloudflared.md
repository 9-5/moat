# Setting Up Moat with Cloudflared (Cloudflare Tunnels)

**Conceptual Overview:**

1.  **Moat:** Runs on your local server (or inside a Docker container on that server), listening on a local port (e.g., `localhost:8000`). It handles authentication and reverse proxies requests to your backend services.
2.  **Backend Services:** These are your actual applications, running locally (e.g., `localhost:3001`, or as Docker containers like `http://my-app-container:80`). Moat needs to be able to reach these on the local network.
3.  **`cloudflared`:** A small daemon from Cloudflare that runs on the same server as Moat. It creates a secure, outbound-only connection to Cloudflare's edge network.
4.  **Cloudflare's Edge:** When a user accesses your public hostname (e.g., `https://app.yourdomain.com`), the request is routed through Cloudflare's global network to your `cloudflared` instance. `cloudflared` then forwards the request to Moat.

**Configuration Steps:**

1.  **Install `cloudflared`:** Follow Cloudflare's official instructions for installing `cloudflared` on your server.
2.  **Create a Tunnel:**
    *   Use `cloudflared tunnel create <tunnel-name>` to create a new tunnel.
    *   Note the tunnel ID (UUID) that `cloudflared` outputs.
3.  **Create a Configuration File:**  `cloudflared` uses a configuration file (usually `~/.cloudflared/config.yml` or `/etc/cloudflared/config.yml`) to define the tunnel's behavior.  Here's a basic example:

    ```yaml
    tunnel: <your-tunnel-id>
    credentials-file: /root/.cloudflared/<your-tunnel-id>.json

    ingress:
      - hostname: moat.yourdomain.com
        service: http://localhost:8000  # Moat's local address
      - hostname: app1.yourdomain.com
        service: http://localhost:3001 # Example backend service.  Moat MUST protect this!
      - hostname: app2.yourdomain.com
        service: http://localhost:3002 # Another example backend service
      - service: http_status:404 # Catch-all rule, required

    originRequest:
        originRequest:
            noTLSVerify: true
    ```

    *   Replace `<your-tunnel-id>` with the actual tunnel ID.
    *   Replace `moat.yourdomain.com` with the desired hostname for accessing Moat itself.  This hostname **must** be configured in your Cloudflare DNS settings. Point it to Cloudflare.
    *   The `service: http://localhost:8000` line tells `cloudflared` to forward requests for `moat.yourdomain.com` to Moat, running locally on port 8000.
    *   The `app1.yourdomain.com` and `app2.yourdomain.com` entries are examples. **Crucially, Moat needs to be configured to proxy these hostnames to your actual backend services.**  You'll define these in Moat's `config.yml` (either statically or via Docker labels).
    *   **noTLSVerify: true** This will instruct Cloudflare to skip TLS verification when connecting to your origin server. This is unsafe, and should only be used for testing. For production, you should use a valid TLS certificate on your origin server.
4.  **Route DNS:** Use Cloudflare Tunnels DNS routing to point your desired hostnames (e.g., `moat.yourdomain.com`, `app1.yourdomain.com`) to the tunnel. You can do this either in the Cloudflare dashboard or using the command line:

    ```bash
    cloudflared tunnel route dns <tunnel-name> moat.yourdomain.com
    cloudflared tunnel route dns <tunnel-name> app1.yourdomain.com
    ```

5.  **Run the Tunnel:** Start the tunnel using:

    ```bash
    cloudflared tunnel run <tunnel-name>
    ```

6.  **Configure Moat:**
    *   In Moat's `config.yml`, set `moat_base_url` to `https://moat.yourdomain.com`. This is **critical** for correct redirects and cookie handling.
    *   Configure Moat to reverse proxy `app1.yourdomain.com` to `http://localhost:3001` and `app2.yourdomain.com` to `http://localhost:3002` (or the actual addresses of your backend services).
    *   Set the `cookie_domain` in Moat's `config.yml` to `.yourdomain.com` for SSO across subdomains.

**Important Considerations:**

*   **HTTPS:** Cloudflare Tunnel provides HTTPS termination by default. Ensure your Moat instance and backend services are configured to handle HTTPS or are running behind a proxy that handles TLS.
*   **Security:** Cloudflare Tunnel creates outbound-only connections, which significantly reduces the attack surface compared to traditional port forwarding.
*   **DNS Propagation:** After creating the DNS records, allow time for propagation.
*   **Moat Configuration:** Double-check that Moat is correctly configured to reverse proxy the hostnames defined in your `cloudflared` configuration to the correct internal services.

**Troubleshooting:**

*   **Cloudflared Connection Issues:**
    *   Check `cloudflared` logs for errors.
    *   Ensure the tunnel is running and properly configured.
    *   Verify the Cloudflare DNS records are correctly pointing to Cloudflare and that your tunnel is routing traffic correctly.
*   **Moat Not Accessible:**
    *   Verify `cloudflared` is routing traffic to Moat's local port (usually 8000).
    *   Check Moat's logs for errors.
    *   Ensure Moat is running and accessible on the local network.
*   **Reverse Proxying Issues:**
    *   Double-check Moat's static service configuration or Docker labels to ensure the hostnames are correctly mapped to the internal service addresses.
    *   Verify your backend services are running and accessible on the local network.
*   **Redirect Loops:**
    *   Verify `moat_base_url` in Moat's `config.yml` is **exactly** `https://moat.yourdomain.com` (or your equivalent).
    *   Check `X-Forwarded-Proto` and `X-Forwarded-Host` headers. Cloudflare tunnels generally set these correctly.
*   **Cookie Issues / Not Staying Logged In:**
    *   Ensure `cookie_domain` in Moat's `config.yml` is correct (e.g., `.yourdomain.com`).
    *   Check browser developer tools to see if cookies are being set for the correct domain.
*   **DNS Issues:** Ensure your DNS records created via `cloudflared tunnel route dns` have propagated. Use `dig` or `nslookup` for your public hostnames.

This detailed guide should help you get Moat up and running securely with Cloudflare Tunnel!