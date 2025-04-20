# Setting Up Moat with Cloudflared (Cloudflare Tunnels)

**Conceptual Overview:**

1.  **Moat:** Runs on your local server (or inside a Docker container on that server), listening on a local port (e.g., `localhost:8000`). It handles authentication and reverse proxies requests to your backend services.
2.  **Backend Services:** These are your actual applications, running locally (e.g., `localhost:3001`, or as Docker containers like `http://my-app-container:80`). Moat needs to be able to reach these on the local network.
3.  **`cloudflared`:** A small daemon from Cloudflare that runs on the same server as Moat. It creates a secure, outbound-only connection to Cloudflare's edge network.
4.  **Cloudflare's Edge:** When a user accesses your public hostname (e.g., `https://my-app.yourdomain.com`), the request is handled by Cloudflare's global network. Cloudflare forwards the request through the tunnel to `cloudflared`.
5.  **Proxying:** `cloudflared` forwards the request to Moat. Moat authenticates the user (if needed). Then Moat reverse proxies the request to the appropriate Backend Service. Finally, the response follows the same path back to the user.

**Steps:**

1.  **Install `cloudflared`:** Follow Cloudflare's official documentation to install `cloudflared` on your server.
2.  **Create a Tunnel:** Use `cloudflared tunnel create <tunnel-name>` to create a new tunnel in your Cloudflare account.
3.  **Configure the Tunnel:** Create a `config.yml` file for `cloudflared`. This file defines how `cloudflared` routes traffic.  A minimal example:

    ```yaml
    tunnel: <your-tunnel-id>
    credentials-file: /root/.cloudflared/<your-tunnel-id>.json

    ingress:
      - hostname: moat.yourdomain.com
        service: http://localhost:8000 # Moat's local address
      - hostname: app1.yourdomain.com
        service: http://localhost:3001 # Example backend app
      - hostname: app2.yourdomain.com
        service: http://my-app-container:80 # Example Docker container
      - service: http_status:404 # Catch-all
    ```

    *   Replace `<your-tunnel-id>` with your actual tunnel ID.
    *   Adjust `hostname` and `service` values to match your desired routing and backend services.
    *   **Crucially, ensure `moat.yourdomain.com` points to your Moat instance.**
4.  **Run the Tunnel:** Start the tunnel with `cloudflared tunnel run <tunnel-name>`.
5.  **Configure DNS Records:** Use `cloudflared tunnel route dns <tunnel-name> <hostname>` to create DNS records in Cloudflare that point your hostnames to the tunnel.
    *   For example: `cloudflared tunnel route dns my-tunnel moat.yourdomain.com`
    *   And: `cloudflared tunnel route dns my-tunnel app1.yourdomain.com`
6.  **Configure Moat:**
    *   Set `moat_base_url` in Moat's `config.yml` to `https://moat.yourdomain.com`. This **must** match the hostname you configured in Cloudflare for Moat.
    *   Set `cookie_domain` in Moat's `config.yml` to `.yourdomain.com` to enable SSO across subdomains.

**Important Considerations:**

*   **Security:** Cloudflare Tunnels create outbound-only connections, enhancing security by eliminating the need to open inbound ports on your server.
*   **HTTPS:** Cloudflare automatically provides HTTPS certificates for your domain.
*   **Subdomains:** This setup assumes you're using subdomains to route traffic to your applications. Adjust the `hostname` values in the `cloudflared` config and Moat's `config.yml` accordingly.
*   **Local Network:** Ensure Moat can access your backend services on your local network (or within your Docker network).
*   **Docker Containers:** If your backend services are Docker containers, use the container name as the hostname in the `cloudflared` config (e.g., `http://my-app-container:80`).

**Troubleshooting:**

*   **Connection Refused:**
    *   Double-check that your backend services are running and accessible on the specified ports.
    *   Verify that `cloudflared` is running and connected to Cloudflare.
    *   Ensure that Moat can reach your backend services.
*   **502 Bad Gateway:** This often indicates a problem with the upstream service (your backend application) or a network issue. Check the logs for both `cloudflared` and your backend services.
*   **Redirect Loops:**
    *   Verify `moat_base_url` in Moat's `config.yml` is **exactly** `https://moat.yourdomain.com` (or your equivalent).
    *   Check `X-Forwarded-Proto` and `X-Forwarded-Host` headers. Cloudflare tunnels generally set these correctly.
*   **Cookie Issues / Not Staying Logged In:**
    *   Ensure `cookie_domain` in Moat's `config.yml` is correct (e.g., `.yourdomain.com`).
    *   Check browser developer tools to see if cookies are being set for the correct domain.
*   **DNS Issues:** Ensure your DNS records created via `cloudflared tunnel route dns` have propagated. Use `dig` or `nslookup` for your public hostnames.

This detailed guide should help you get Moat up and running securely with Cloudflare Tunnel!