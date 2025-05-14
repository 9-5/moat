# Setting Up Moat with Cloudflared (Cloudflare Tunnels)

**Conceptual Overview:**

1.  **Moat:** Runs on your local server (or inside a Docker container on that server), listening on a local port (e.g., `localhost:8000`). It handles authentication and reverse proxies requests to your backend services.
2.  **Backend Services:** These are your actual applications, running locally (e.g., `localhost:3001`, or as Docker containers like `http://my-app-container:80`). Moat needs to be able to reach these on the local network.
3.  **`cloudflared`:** A small daemon from Cloudflare that runs on the same server as Moat. It creates a secure, outbound-only connection to Cloudflare's edge network.
4.  **Cloudflare's Edge:** When a user accesses your public-facing hostname, Cloudflare's edge servers receive the request. `cloudflared` ensures that **only** Cloudflare can access your Moat instance.

**Configuration Steps:**

1.  **Install `cloudflared`:** Follow Cloudflare's official instructions to install `cloudflared` on your server.
2.  **Create a Tunnel:**
    *   Run `cloudflared tunnel create <tunnel-name>`. This will give you a Tunnel ID.
    *   A tunnel definition file `~/.cloudflared/<tunnel-name>.json` will be created.
3.  **Create DNS Records:**
    *   Using the Tunnel ID, create DNS records that point to your tunnel. This is done via `cloudflared tunnel route dns <tunnel-name> <hostname>`.  For example: `cloudflared tunnel route dns my-tunnel moat.yourdomain.com` (for Moat itself) and `cloudflared tunnel route dns my-tunnel app1.yourdomain.com` (for an application).
4.  **Configure `cloudflared` to Route Traffic to Moat:**
    *   Create a `config.yml` file for `cloudflared` (typically in `~/.cloudflared/config.yml`).  This file will tell `cloudflared` where to send traffic.  A basic configuration looks like this:

        ```yaml
        tunnel: <your-tunnel-id>
        credentials-file: /root/.cloudflared/<your-tunnel-name>.json

        ingress:
          - hostname: moat.yourdomain.com
            service: http://localhost:8000  # Moat's local address

          - hostname: app1.yourdomain.com
            service: http://localhost:3001  # Example backend app
            # Optionally, add more hostnames and services.

          - service: http_status:404 # Catch-all rule

        ```
5.  **Run the Tunnel:**  Start the tunnel with `cloudflared tunnel run <tunnel-name>`.

**Important Moat Configuration Considerations:**

*   **`moat_base_url`:**  This setting in Moat's `config.yml` is **crucial**.  It tells Moat what its *public* URL is.  When using Cloudflare Tunnels, this must be set to the Cloudflare-proxied hostname (e.g., `https://moat.yourdomain.com`).  If not, Moat will generate incorrect redirect URLs, leading to login loops.
*   **Cookie Domain:** The `cookie_domain` setting should match your domain (e.g., `.yourdomain.com`) for SSO to work correctly.
*   **HTTPS:** Even though traffic between `cloudflared` and Moat is unencrypted (http://localhost:8000), the connection between the user and Cloudflare's edge is **always** HTTPS.

**Troubleshooting:**

*   **Cloudflare Tunnel Connection Issues:**
    *   Check `cloudflared` logs (usually in `/var/log/cloudflared/`) for connection errors.
    *   Ensure the tunnel is running with `cloudflared tunnel run <tunnel-name>`.
    *   Verify the tunnel ID in `~/.cloudflared/config.yml` is correct.
*   **Moat Not Accessible:**
    *   Double-check the `ingress` section of your `cloudflared` config.yml.  Is the hostname correctly mapped to Moat's local port (usually 8000)?
    *   Ensure Moat is running and accessible on `localhost:8000` (or whatever port you configured).
    *   Check firewall rules to make sure `cloudflared` can connect to Moat.
*   **Authentication Problems / Redirect Loops:** This is almost always due to an incorrect `moat_base_url` setting. It **must** be the public hostname proxied by Cloudflare, including the `https://` prefix.  Moat needs to generate correct URLs for redirects after successful authentication and for reverse proxying.
*   **Backend Applications Not Accessible:** Similar to Moat itself, ensure the `ingress` rules in `cloudflared` config.yml are correctly routing traffic to your backend services.  Verify Moat can reach these services on their local addresses.

**Example Scenario:**

Let's say you have Moat running on a server, and you want to protect two applications:

*   `moat.example.com`:  Moat itself (admin UI, login page)
*   `app1.example.com`: Your first application
*   `app2.example.com`: Your second application

Your `cloudflared` config.yml might look like:

```yaml
tunnel: your-tunnel-id
credentials-file: /root/.cloudflared/your-tunnel.json

ingress:
  - hostname: moat.example.com
    service: http://localhost:8000

  - hostname: app1.example.com
    service: http://localhost:3001

  - hostname: app2.example.com
    service: http://localhost:3002

  - service: http_status:404
```

And your Moat `config.yml` would need:

```yaml
moat_base_url: https://moat.example.com
cookie_domain: .example.com
```

**Important Security Notes:**

*   `cloudflared` creates an outbound-only connection.  No inbound ports need to be opened on your server's firewall. This drastically reduces the attack surface.
*   Always use HTTPS for `moat_base_url`.
*   Ensure your backend applications are *only* accessible through Moat.  Block direct access to their ports from the outside world.

By following these steps, you can securely expose your self-hosted applications to the internet using Cloudflare Tunnels and Moat for authentication and reverse proxying.