# Setting Up Moat with Cloudflared (Cloudflare Tunnels)

**Conceptual Overview:**

1.  **Moat:** Runs on your local server (or inside a Docker container on that server), listening on a local port (e.g., `localhost:8000`). It handles authentication and reverse proxies requests to your backend services.
2.  **Backend Services:** These are your actual applications, running locally (e.g., `localhost:3001`, or as Docker containers like `http://my-app-container:80`). Moat needs to be able to reach these on the local network.
3.  **`cloudflared`:** A small daemon from Cloudflare that runs on the same server as Moat. It creates a secure, outbound-only connection to Cloudflare's edge network.
4.  **Cloudflare's Edge:** When a user accesses your public hostname, Cloudflare's edge network forwards the request through the tunnel to `cloudflared`.  `cloudflared` then sends the request to Moat, which authenticates the user and proxies the request to the appropriate backend service.

**Configuration Steps:**

1.  **Install `cloudflared`:** Follow Cloudflare's official documentation to install `cloudflared` on your server.
2.  **Create a Tunnel:** Use `cloudflared tunnel create <tunnel-name>` to create a new tunnel.
3.  **Create DNS Records:** Use `cloudflared tunnel route dns <tunnel-name> <your.domain.com>` to point your desired domain or subdomain to the tunnel.
4.  **Configure `config.yml`:**  This is the crucial part.  You **must** set `moat_base_url` to the **public-facing URL served by Cloudflare** (e.g., `https://moat.yourdomain.com`).  Also configure `cookie_domain` appropriately (e.g. `.yourdomain.com`).

```yaml
moat_base_url: https://moat.yourdomain.com
cookie_domain: .yourdomain.com
```

5.  **Create a Tunnel Configuration File:**  `cloudflared` uses a config file (typically `~/.cloudflared/config.yml`) to define how to route traffic.  You need to tell it to route traffic for your `moat_base_url` to Moat's local port:

```yaml
tunnel: <your-tunnel-id>
credentials-file: /root/.cloudflared/<your-tunnel-id>.json
ingress:
  - hostname: moat.yourdomain.com  # Replace with your moat_base_url
    service: http://localhost:8000  # Or the port Moat is listening on
  - service: http_status:404
```

    *   **Important**: The `hostname` in your `cloudflared` config must **exactly** match your `moat_base_url` hostname in `config.yml`.
    *   You can add other services to the `ingress` list, routing them to different local ports or Docker containers.  These would be services protected by Moat.  Ensure Moat has static service entries, or can discover these containers through docker labels, to protect them.

6.  **Run the Tunnel:**  Start the tunnel using `cloudflared tunnel run <tunnel-name>`.

**Troubleshooting Cloudflared with Moat**

*   **General Connectivity Issues:**
    *   Ensure the `cloudflared` daemon is running. Check its logs for errors.
    *   Verify that your tunnel is correctly configured in Cloudflare's dashboard.
    *   Double-check that `cloudflared` can reach Moat on `localhost:8000` (or the port Moat is listening on). Try `curl http://localhost:8000` from the server.
*   **Authentication Problems / Redirect Loops:** The most common cause is an incorrect `moat_base_url` in Moat's `config.yml`. It **must** be the public-facing URL served by Cloudflare. Clear your browser's cookies for the domain to ensure there are no conflicts.
*   **"Too many redirects"**: Check that `moat_base_url` is correct and that you don't have conflicting redirects set up in Cloudflare Page Rules.
*   **400 Bad Request:** This can sometimes occur if the `Host` header being sent to your backend application doesn't match what it expects. This is less common with Cloudflare tunnels but can occur.  You might need to adjust header settings in Cloudflare or within Moat's proxying.
*   **SSO Cookie Issues:** Ensure `cookie_domain` is set correctly. It should be the top-level domain for all your services (e.g., `.yourdomain.com`). If this is incorrect, users may be continuously redirected to the login page.

**Important Considerations:**

*   **Security:** Cloudflare Tunnels provide a secure, outbound-only connection.  This significantly reduces the attack surface of your server.
*   **HTTPS:** Cloudflare handles HTTPS termination.  Moat itself does not need to be configured with SSL certificates.
*   **Subdomains:** You can use subdomains to route traffic to different services. For example, `app1.yourdomain.com` could point to one service, and `app2.yourdomain.com` to another, all proxied through Moat.  Ensure your `cloudflared` config file and Moat's configuration (static services or Docker labels) are correctly configured for each subdomain.
*   **Origin CA Certificates (Optional):** For enhanced security, you can use Cloudflare's Origin CA certificates to encrypt traffic between Cloudflare and your origin server. This adds another layer of encryption on top of the tunnel's security, but is generally not required.

This detailed guide should help you get Moat up and running securely with Cloudflare Tunnel!