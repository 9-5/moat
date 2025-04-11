# Setting Up Moat with Cloudflared (Cloudflare Tunnels)

**Conceptual Overview:**

1.  **Moat:** Runs on your local server (or inside a Docker container on that server), listening on a local port (e.g., `localhost:8000`). It handles authentication and reverse proxies requests to your backend services.
2.  **Backend Services:** These are your actual applications, running locally (e.g., `localhost:3001`, or as Docker containers like `http://my-app-container:80`). Moat needs to be able to reach these on the local network.
3.  **`cloudflared`:** A small daemon from Cloudflare that runs on the same server as Moat. It creates a secure, outbound-only connection to Cloudflare's edge network.
4.  **Cloudflare's Edge:** When a user accesses your publicly accessible services, the requests first hit Cloudflare's edge network. Cloudflare then uses the tunnel created by `cloudflared` to securely forward the traffic to Moat.

**Configuration Steps:**

1.  **Install `cloudflared`:** Follow Cloudflare's official documentation to install `cloudflared` on your server.
2.  **Create a Tunnel:**
    ```bash
    cloudflared tunnel create <your_tunnel_name>
    ```
3.  **Create a DNS Record:** After creating the tunnel, `cloudflared` will give you a Tunnel ID. Create a DNS record in Cloudflare that points your desired hostname (e.g., `moat.yourdomain.com`) to the tunnel:
    ```bash
    cloudflared tunnel route dns <your_tunnel_name> moat.yourdomain.com
    ```
4.  **Configure the Tunnel:** Create a `config.yml` file for `cloudflared` (usually located in `~/.cloudflared/config.yml`).  This file tells `cloudflared` how to route traffic.  Crucially, you'll route traffic for your Moat subdomain to Moat's local address.

    ```yaml
    tunnel: <your_tunnel_id>
    credentials-file: /root/.cloudflared/<your_tunnel_id>.json
    ingress:
      - hostname: moat.yourdomain.com
        service: http://localhost:8000  # Moat's local address
      - service: hello_world
      - service: http_status:404
    ```

    **Important Considerations:**

    *   **`hostname`**: This must match the DNS record you created in Cloudflare.
    *   **`service`**: This is the local address where `cloudflared` will forward traffic.  Since we're configuring access to Moat, it should point to the address where Moat is listening (typically `http://localhost:8000`).  Moat will then handle authentication and proxying to your backend services.
    * The "hello_world" and "http_status:404" entries are the default values in official cloudflared config. They are not related to Moat and can be removed.

5.  **Start the Tunnel:**
    ```bash
    cloudflared tunnel run <your_tunnel_name>
    ```

**Moat Configuration:**

1.  **`moat_base_url`:** In Moat's `config.yml`, set `moat_base_url` to the **public URL** you configured in Cloudflare (e.g., `https://moat.yourdomain.com`).  This is essential for correct redirects and cookie handling.
2.  **`cookie_domain`:** Set the `cookie_domain` in Moat's `config.yml` to match your domain (e.g., `.yourdomain.com`).
3.  **HTTPS:** Cloudflare Tunnel provides HTTPS encryption between Cloudflare's edge and your server.  Moat should also be configured to use HTTPS if possible, although Cloudflare Tunnels handles the encryption to the internet.

**Example `config.yml` (Moat):**

```yaml
listen_host: 0.0.0.0
listen_port: 8000
secret_key: "YOUR_SECRET_KEY"
database_url: sqlite+aiosqlite:///./moat.db
moat_base_url: https://moat.yourdomain.com  # Important!
cookie_domain: .yourdomain.com            # Important!
docker_monitor_enabled: true
moat_label_prefix: moat
```

**Important Notes:**

*   **Cloudflare's Origin CA Certificates (Optional):** For even stronger security, you can use Cloudflare's Origin CA Certificates to authenticate connections between Cloudflare and your origin server. This is beyond the scope of this basic guide but is highly recommended for production deployments.
*   **Firewall:** Ensure your firewall allows traffic from `cloudflared` to Moat's port (e.g., 8000). You should **not** expose Moat directly to the internet; `cloudflared` provides the secure tunnel.
*   **Subdomain Routing:** The above configuration routes *all* traffic for `moat.yourdomain.com` to Moat. To route different subdomains to different services, you'd create additional tunnels or use Cloudflare's Page Rules.  This is not covered here.

**Troubleshooting:**

*   **`cloudflared` Connection Issues:** Check `cloudflared`'s logs for connection errors. Ensure your tunnel is running and properly configured. Verify that `cloudflared` can reach Moat on `localhost:8000`.
*   **Moat Not Accessible:** Double-check your DNS records and `cloudflared` configuration. Ensure the hostname in `cloudflared`'s `config.yml` matches your DNS record **exactly**.
*   **Authentication Issues/Redirect Loops:** The most common cause is an incorrect `moat_base_url` in Moat's `config.yml`. It **must** be the public-facing URL served by Cloudflare. Clear your browser's cookies for the domain to ensure there are no conflicts.
*   **"Too many redirects"**: Check that `moat_base_url` is correct and that you don't have conflicting redirects set up in Cloudflare Page Rules.
*   **400 Bad Request:** This can sometimes occur if the `Host` header being sent to your backend application doesn't match what it expects. This is less common with Cloudflare tunnels but can occur.  You might need to adjust header settings in Cloudflare or within Moat's pr

... (FILE CONTENT TRUNCATED) ...

This detailed guide should help you get Moat up and running securely with Cloudflare Tunnel!