# Setting Up Moat with Cloudflared (Cloudflare Tunnels)

**Conceptual Overview:**

1.  **Moat:** Runs on your local server (or inside a Docker container on that server), listening on a local port (e.g., `localhost:8000`). It handles authentication and reverse proxies requests to your backend services.
2.  **Backend Services:** These are your actual applications, running locally (e.g., `localhost:3001`, or as Docker containers like `http://my-app-container:80`). Moat needs to be able to reach these on the local network.
3.  **`cloudflared`:** A small daemon from Cloudflare that runs on the same server as Moat. It creates a secure, outbound-only connection to Cloudflare's edge network.
4.  **Cloudflare's Edge:** When a user accesses your public services, the request is routed through Cloudflare's global network and then securely passed to your server via the `cloudflared` tunnel.

**Configuration Steps:**

1.  **Install `cloudflared`:** Follow Cloudflare's official documentation to install `cloudflared` on your server.
2.  **Authenticate `cloudflared`:** Run `cloudflared tunnel login` and authenticate with your Cloudflare account.
3.  **Create a Tunnel:** Use `cloudflared tunnel create <tunnel-name>` to create a new tunnel.  Take note of the Tunnel ID.
4.  **Create a Configuration File:** `cloudflared` uses a YAML configuration file. Create a file (e.g., `~/.cloudflared/config.yml`) with the following structure:

```yaml
tunnel: <your-tunnel-id>
credentials-file: /root/.cloudflared/<your-tunnel-id>.json

ingress:
  - hostname: moat.yourdomain.com
    service: http://localhost:8000 # Moat's local address
  - hostname: app1.yourdomain.com
    service: http://localhost:3001 # Example backend service
  - hostname: app2.yourdomain.com
    service: http://my-app-container:80 # Example Docker container
  - service: http_status:404 # Catch-all

```

*   **`tunnel`**:  The Tunnel ID you obtained when creating the tunnel.
*   **`credentials-file`**: The path to the credentials file created during authentication.
*   **`ingress`**: Defines how traffic is routed.
    *   **`hostname`**: The public hostname for your service.
    *   **`service`**:  The local address where your service is running. This is crucial!  For Moat itself, this will typically be `http://localhost:8000` (or the port you've configured Moat to listen on).  For Docker containers, use the container name and port (e.g., `http://my-app-container:80`).  Make sure Moat can resolve these container names.
*   **DNS Records:** Cloudflare tunnels need DNS records pointed to them.
    *   `cloudflared tunnel route dns <tunnel-name> moat.yourdomain.com`
    *   `cloudflared tunnel route dns <tunnel-name> app1.yourdomain.com`
    *   `cloudflared tunnel route dns <tunnel-name> app2.yourdomain.com`
5.  **Run the Tunnel:** Start the tunnel with `cloudflared tunnel run <tunnel-name>`.

**Moat Configuration:**

*   **`config.yml`:**  You need to configure `moat_base_url` and `cookie_domain` in Moat's `config.yml`.
    *   **`moat_base_url`:** This **must** be the public URL you've assigned to Moat in Cloudflare (e.g., `https://moat.yourdomain.com`).  This tells Moat where it's being accessed from externally, which is vital for redirects and cookie management.
    *   **`cookie_domain`:**  Set this to your domain (e.g., `.yourdomain.com`) to ensure cookies work correctly across subdomains.

```yaml
listen_host: 0.0.0.0
listen_port: 8000
secret_key: "YOUR_VERY_SECRET_KEY_CHANGE_THIS_NOW_PLEASE"
access_token_expire_minutes: 60
database_url: sqlite+aiosqlite:///./moat.db
moat_base_url: https://moat.yourdomain.com # IMPORTANT: Cloudflare Tunnel URL
cookie_domain: .yourdomain.com          # IMPORTANT: Your domain
docker_monitor_enabled: true
moat_label_prefix: moat
static_services: []
```

**Important Considerations:**

*   **Local Network Access:** Ensure Moat can access your backend services on your local network. If your services are in Docker containers, Moat needs to be able to resolve their container names.
*   **HTTPS:** Cloudflare Tunnel provides HTTPS termination at the edge.  Moat itself doesn't need to handle HTTPS directly in this setup.
*   **Security:** Cloudflare Tunnel creates outbound-only connections, enhancing security.

**Troubleshooting:**

*   **Ensure `cloudflared` is Running:** Check the `cloudflared` logs for errors.
*   **Verify Tunnel Configuration:** Double-check your `config.yml` file for typos and incorrect paths.
*   **Moat's `config.yml`:**  Pay close attention to `moat_base_url` and `cookie_domain`. These are critical for proper functioning with reverse proxying.
*   **Cloudflare DNS Propagation:**  DNS changes can take time to propagate.

**Common Issues and Solutions:**

*   **502/504 Errors:** Usually indicate a problem with the connection between `cloudflared` and your local services.
    *   Double-check the `service` definitions in your `cloudflared` `config.yml`.  Are the ports correct? Can `cloudflared` reach those addresses?
    *   Make sure the services are actually running and listening on the specified ports.
    *   Check firewall rules that might be blocking traffic.
*   **Infinite Redirect Loops when Authenticating with Moat:** This is almost always due to an incorrect `moat_base_url` in Moat's `config.yml`. It **must** be the full public URL served by Cloudflare Tunnel for Moat (e.g., `https://moat.yourdomain.com`).
*   **"Too many redirects" Error in Browser:** Similar to redirect loops. Check `moat_base_url`.
*   **Cookie Issues / Not Staying Logged In:** Ensure `cookie_domain` in Moat's `config.yml` is correct (e.g., `.yourdomain.com`). Clear your browser's cookies and cache.
*   **Services Not Accessible After Authentication:**
    *   Verify the service definitions in `cloudflared`'s `config.yml`.
    *   Check that the hostnames in `cloudflared`'s config match what you're trying to access.
    *   If using Docker, make sure Moat can resolve the container names.
*   **Cloudflare Dashboard:** Use the Cloudflare dashboard to monitor your tunnel's health and traffic.  Look for errors or unusual activity.

**Advanced Configuration:**

*   **Load Balancing:** Cloudflare Tunnel supports load balancing across multiple instances of your services.
*   **Access Policies:** Cloudflare Access can be used to add another layer of authentication and authorization on top of Moat.
*   **Mutual TLS (mTLS):**  You can configure Cloudflare Tunnel to use mTLS for even stronger security.

By following these steps and paying attention to the troubleshooting tips, you can successfully set up Moat with Cloudflare Tunnel for secure and reliable reverse proxying.

**Example `cloudflared` config (for reference):**

```yaml
tunnel: aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee
credentials-file: /root/.cloudflared/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee.json
ingress:
  - hostname: moat.example.com
    service: http://localhost:8000
  - hostname: app1.example.com
    service: http://127.0.0.1:3001
  - hostname: app2.example.com
    service: http://my-docker-app:80
  - service: http_status:404
```

**Example Moat `config.yml` (for reference):**

```yaml
listen_host: 0.0.0.0
listen_port: 8000
secret_key: "YOUR_VERY_SECRET_KEY_CHANGE_THIS_NOW_PLEASE"
access_token_expire_minutes: 60
database_url: sqlite+aiosqlite:///./moat.db
moat_base_url: https://moat.example.com
cookie_domain: .example.com
docker_monitor_enabled: true
moat_label_prefix: moat
static_services: []
```

Remember to replace the placeholder values with your actual configuration.

This detailed guide should help you get Moat up and running securely with Cloudflare Tunnel!