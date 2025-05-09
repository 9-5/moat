# Setting Up Moat with Cloudflared (Cloudflare Tunnels)

**Conceptual Overview:**

1.  **Moat:** Runs on your local server (or inside a Docker container on that server), listening on a local port (e.g., `localhost:8000`). It handles authentication and reverse proxies requests to your backend services.
2.  **Backend Services:** These are your actual applications, running locally (e.g., `localhost:3001`, or as Docker containers like `http://my-app-container:80`). Moat needs to be able to reach these on the local network.
3.  **`cloudflared`:** A small daemon from Cloudflare that runs on the same server as Moat. It creates a secure, outbound-only connection to Cloudflare's edge network.
4.  **Cloudflare's Edge:** When a user accesses your public hostname, Cloudflare's edge servers forward the traffic through the tunnel to your server, where `cloudflared` passes it to Moat. Moat then authenticates the user and reverse proxies the request to your backend service.

**Steps:**

1.  **Install and Configure `cloudflared`:** Follow Cloudflare's official documentation to install `cloudflared` on your server. Authenticate it with your Cloudflare account and create a tunnel.

2.  **Create DNS Records:** Use `cloudflared tunnel route dns` command to create DNS records in Cloudflare that point your desired hostnames (e.g., `app1.yourdomain.com`, `app2.yourdomain.com`) to the tunnel.

3.  **Configure Moat:**

    *   **`moat_base_url`:**  Set this in `config.yml` to your Moat's public hostname (e.g., `https://moat.yourdomain.com`). This is crucial for redirects to work correctly.
    *   **`cookie_domain`:**  Set this to your domain (e.g., `.yourdomain.com`) so cookies work across subdomains.
    *   **Backend Services:** Configure your backend services in Moat either via Docker labels (if they are Dockerized) or as static services in `config.yml`.  Make sure the `target_url` for each service is reachable from the Moat container.

4.  **Run Moat and `cloudflared`:** Start both Moat and `cloudflared` on your server.

**Example `cloudflared` command:**

```bash
cloudflared tunnel run <your_tunnel_id>
```

**Important Considerations:**

*   **TLS:** Cloudflare Tunnel encrypts traffic between your server and Cloudflare's edge.  You can run your backend services on plain HTTP (e.g., `http://localhost:3000`) as the traffic is already secured by the tunnel.  Moat should be configured with `https` for its `moat_base_url`.
*   **Health Checks:** Configure Cloudflare Health Checks to monitor your Moat instance.  This allows Cloudflare to automatically failover to a different instance if your Moat server becomes unavailable.

**Troubleshooting:**

*   **Verify Connectivity:** Use `curl` from within the Moat container (or from the server if running Moat directly) to verify that Moat can reach your backend services.
*   **Cloudflare Dashboard:** Check the Cloudflare dashboard for any errors related to your tunnel or DNS records.
*   **Moat Logs:** Examine Moat's logs for any authentication or proxying errors.
*   **`cloudflared` Logs:** Check `cloudflared`'s logs for tunnel connection issues or routing problems.
*   **Browser Developer Tools:** Use your browser's developer tools to inspect network requests and cookies. This can help identify redirect loops or cookie domain issues.
*   **Ensure correct `moat_base_url`:** This is the most common cause of redirect loops when using reverse proxying.
*   **Headers:** Cloudflare tunnels automatically set common headers like `X-Forwarded-For` and `X-Forwarded-Proto`, which Moat uses for correct proxying.
*   **Consider using `warp-routing`:** `warp-routing` can improve performance by routing traffic directly to the nearest Cloudflare data center, bypassing the public internet for a portion of the journey. Enable this in your tunnel configuration.

**Common Issues and Solutions:**

*   **"502 Bad Gateway" errors:**  This often indicates that Moat cannot reach your backend service. Double-check the `target_url` in Moat's configuration and verify network connectivity.
*   **Redirect Loops:**
    *   Verify `moat_base_url` in Moat's `config.yml` is **exactly** `https://moat.yourdomain.com` (or your equivalent).
    *   Check `X-Forwarded-Proto` and `X-Forwarded-Host` headers. Cloudflare tunnels generally set these correctly.
*   **Cookie Issues / Not Staying Logged In:**
    *   Ensure `cookie_domain` in Moat's `config.yml` is correct (e.g., `.yourdomain.com`).
    *   Check browser developer tools to see if cookies are being set for the correct domain.
*   **DNS Issues:** Ensure your DNS records created via `cloudflared tunnel route dns` have propagated. Use `dig` or `nslookup` for your public hostnames.

This detailed guide should help you get Moat up and running securely with Cloudflare Tunnel!