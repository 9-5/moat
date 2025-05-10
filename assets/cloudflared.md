# Setting Up Moat with Cloudflared (Cloudflare Tunnels)

**Conceptual Overview:**

1.  **Moat:** Runs on your local server (or inside a Docker container on that server), listening on a local port (e.g., `localhost:8000`). It handles authentication and reverse proxies requests to your backend services.
2.  **Backend Services:** These are your actual applications, running locally (e.g., `localhost:3001`, or as Docker containers like `http://my-app-container:80`). Moat needs to be able to reach these on the local network.
3.  **`cloudflared`:** A small daemon from Cloudflare that runs on the same server as Moat. It creates a secure, outbound-only connection to Cloudflare's edge network.
4.  **Cloudflare's Edge:** When a user accesses your public application hostname (e.g., `https://app.yourdomain.com`), the request is routed through Cloudflare's network.
5.  **The Tunnel:** Cloudflared establishes an encrypted tunnel between your server and Cloudflare's edge. This tunnel is **outbound-only**, meaning no inbound ports need to be opened on your firewall.
6.  **Reverse Proxying:** Cloudflare's edge network reverse proxies the traffic through the tunnel to your Moat instance. Moat authenticates the user. If authorized, Moat then reverse proxies the traffic to your backend service.

**Configuration Steps:**

1.  **Install `cloudflared`:** Follow Cloudflare's official documentation to install `cloudflared` on your server.
2.  **Authenticate `cloudflared`:** Run `cloudflared login` and authenticate with your Cloudflare account.
3.  **Create a Tunnel:** Run `cloudflared tunnel create <tunnel-name>`. This creates a tunnel in your Cloudflare account.
4.  **Configure the Tunnel:** Create a `config.yml` file for `cloudflared` (usually located in `~/.cloudflared/config.yml`). This file defines how traffic is routed through the tunnel.  Here's an example:

```yaml
tunnel: <your-tunnel-id>
credentials-file: /root/.cloudflared/<your-tunnel-id>.json

ingress:
  - hostname: moat.yourdomain.com # Your Moat's public hostname
    service: http://localhost:8000  # Moat's local address
  - hostname: app1.yourdomain.com # Public hostname for app1
    service: http://localhost:3001 # Local address for app1
  - hostname: app2.yourdomain.com # Public hostname for app2
    service: http://localhost:3002 # Local address for app2
  - service: http_status:404 # Catch-all 404
```

    *   Replace `<your-tunnel-id>` with the actual tunnel ID.
    *   Replace `moat.yourdomain.com` with the public hostname you want to use for your Moat instance.
    *   Ensure the `service` entries point to the correct **local** addresses of Moat and your backend services.
    *   **Important**: The tunnel needs to route traffic to Moat. Moat then handles authentication and further proxying.

5.  **Run the Tunnel:** Start the tunnel using `cloudflared tunnel run <tunnel-name>`.

6.  **DNS Records:** After creating the tunnel, `cloudflared` will output instructions for creating DNS records in Cloudflare.  These records point your public hostnames to the Cloudflare tunnel. Alternatively, use: `cloudflared tunnel route dns <tunnel-name> <hostname> <origin>` to configure the DNS records.

7.  **Moat Configuration:**

    *   Set `moat_base_url` in Moat's `config.yml` to your public Moat hostname (e.g., `https://moat.yourdomain.com`).  **This is crucial.**
    *   Set `cookie_domain` in Moat's `config.yml` appropriately (e.g., `.yourdomain.com`).

**Example Scenario:**

Let's say you have:

*   Moat running on `localhost:8000`
*   Application 1 running on `localhost:3001`
*   Application 2 running on `localhost:3002`
*   Your domain is `yourdomain.com`

You would:

1.  Create a Cloudflare Tunnel.
2.  Configure your `cloudflared` config to route:
    *   `moat.yourdomain.com` to `http://localhost:8000`
    *   `app1.yourdomain.com` to `http://localhost:3001`
    *   `app2.yourdomain.com` to `http://localhost:3002`
3.  Create DNS records in Cloudflare that point `moat.yourdomain.com`, `app1.yourdomain.com`, and `app2.yourdomain.com` to your Cloudflare Tunnel.
4.  Set `moat_base_url: https://moat.yourdomain.com` in Moat's `config.yml`.
5.  Set `cookie_domain: .yourdomain.com` in Moat's `config.yml`.

**Important Considerations:**

*   **HTTPS:** Cloudflare Tunnel provides automatic HTTPS encryption.  You do **not** need to configure HTTPS certificates on your origin server (the server running Moat). Cloudflare handles the SSL termination.
*   **Security:** Cloudflare Tunnel creates outbound-only connections, significantly improving security by eliminating the need to open inbound ports.
*   **Subdomains:** Using subdomains (e.g., `app1.yourdomain.com`) is the recommended approach for routing traffic to different applications.
*   **Port Conflicts:** Ensure that the ports you are using for your services (e.g., 8000, 3001, 3002) are not blocked by your firewall. However, these ports only need to be accessible **locally** on your server. Cloudflare Tunnel handles the public-facing connectivity.
*   **Health Checks:** Cloudflare can perform health checks on your origin server to ensure that it is up and running.
*   **Zero Trust:** Cloudflare offers a "Zero Trust" platform that provides additional security features, such as user authentication and access control policies.  Moat provides similar functionality, so you can choose the solution that best fits your needs.  Using both can offer enhanced security.

**Troubleshooting:**

*   **Connection Refused Errors:**
    *   Double-check that your services are running on the correct ports.
    *   Verify that the `service` entries in your `cloudflared` config point to the correct **local** addresses.
    *   Ensure no firewall rules are blocking connections between `cloudflared` and your services **on the local server**.
*   **"Bad Gateway" Errors:** This usually indicates a problem with reverse proxying.
    *   Check Moat's logs for errors.
    *   Verify that Moat can reach your backend services.
    *   Ensure `moat_base_url` is configured correctly in Moat's `config.yml`.  This is critical for correct redirects and cookie handling during authentication and reverse proxying.
*   **Redirect Loops:**
    *   Verify `moat_base_url` in Moat's `config.yml` is **exactly** `https://moat.yourdomain.com` (or your equivalent).
    *   Check `X-Forwarded-Proto` and `X-Forwarded-Host` headers. Cloudflare tunnels generally set these correctly.
*   **Cookie Issues / Not Staying Logged In:**
    *   Ensure `cookie_domain` in Moat's `config.yml` is correct (e.g., `.yourdomain.com`).
    *   Check browser developer tools to see if cookies are being set for the correct domain.
*   **DNS Issues:** Ensure your DNS records created via `cloudflared tunnel route dns` have propagated. Use `dig` or `nslookup` for your public hostnames.

This detailed guide should help you get Moat up and running securely with Cloudflare Tunnel!