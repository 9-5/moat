# Setting Up Moat with Cloudflared (Cloudflare Tunnels)

**Conceptual Overview:**

1.  **Moat:** Runs on your local server (or inside a Docker container on that server), listening on a local port (e.g., `localhost:8000`). It handles authentication and reverse proxies requests to your backend services.
2.  **Backend Services:** These are your actual applications, running locally (e.g., `localhost:3001`, or as Docker containers like `http://my-app-container:80`). Moat needs to be able to reach these on the local network.
3.  **`cloudflared`:** A small daemon from Cloudflare that runs on the same server as Moat. It creates a secure, outbound-only connection to Cloudflare's edge network.
4.  **Cloudflare's Edge:** When a user accesses your public application, the request first hits Cloudflare's global network. Cloudflare then forwards the request through the secure tunnel established by `cloudflared` to your Moat instance.
5.  **Reverse Proxying:** Moat authenticates the user.  If successful, it then reverse proxies the request to the appropriate backend service based on the hostname.

**Configuration Steps:**

1.  **Install `cloudflared`:** Follow Cloudflare's official documentation to install `cloudflared` on your server.
2.  **Create a Tunnel:** Use `cloudflared tunnel create <tunnel-name>` to create a new tunnel in your Cloudflare account.
3.  **Configure DNS:**  Use `cloudflared tunnel route dns <tunnel-name> <hostname>` to point your desired hostname (e.g., `moat.yourdomain.com`) to the tunnel.  This creates a DNS record in Cloudflare that routes traffic to your tunnel.  Repeat this step for each hostname you want to expose through the tunnel.
4.  **Create a Configuration File:** Cloudflared uses a configuration file (typically `~/.cloudflared/config.yml`) to define how traffic is routed.  Here's an example configuration:

    ```yaml
    tunnel: <your-tunnel-id>
    credentials-file: /root/.cloudflared/<your-tunnel-id>.json # Adjust path as needed
    ingress:
      - hostname: moat.yourdomain.com
        service: http://localhost:8000  # Moat's local address
      - hostname: app1.yourdomain.com
        service: http://localhost:3001  # Example backend service
      - hostname: app2.yourdomain.com
        service: http://my-app-container:80 # Example Docker container
      - service: http_status:404 # Default to 404 if no other route matches
    ```

    *   **`tunnel`:** Your tunnel's UUID.
    *   **`credentials-file`:** Path to the credentials file for your tunnel.
    *   **`ingress`:** Defines how traffic is routed based on hostname.  Each entry specifies a hostname and the corresponding service to proxy to. `http://localhost:8000` points to your Moat instance.  Other entries point to your backend services.
    *   **`service: http_status:404`:**  A catch-all that returns a 404 error if no other ingress rule matches.  **Important:** Place this *last* in the `ingress` list.

5.  **Run the Tunnel:** Start the tunnel using `cloudflared tunnel run <tunnel-name>`.

6.  **Configure Moat:**
    *   Set `moat_base_url` in Moat's `config.yml` to your public hostname (e.g., `https://moat.yourdomain.com`). This is **critical** for correct redirects and cookie handling.
    *   Set `cookie_domain` in Moat's `config.yml` to your domain (e.g., `.yourdomain.com`) for SSO across subdomains.

**Important Considerations:**

*   **HTTPS:** Cloudflare Tunnel provides HTTPS termination by default. Moat itself doesn't necessarily need to use HTTPS internally (it can listen on `http://localhost:8000`), as the connection between `cloudflared` and Cloudflare's edge is already encrypted. However, setting `moat_base_url` to `https://` is vital for correct cookie settings and redirect behavior.
*   **Security:** Cloudflare Tunnel creates an outbound-only connection. This significantly enhances security as you don't need to open any inbound ports on your server.
*   **Docker:** If your backend services are running in Docker containers, ensure that Moat can reach them on the local network (e.g., by using the container name as the hostname in the `target_url`).
*   **Health Checks:** Cloudflare can perform health checks on your tunnel to ensure that your Moat instance is running.  Refer to Cloudflare's documentation for configuring health checks.

**Troubleshooting:**

*   **Tunnel Not Connecting:**
    *   Verify that `cloudflared` is running and properly configured. Check its logs for errors.
    *   Ensure your tunnel is listed in your Cloudflare account.
    *   Double-check the `credentials-file` path in your `config.yml`.
*   **Cannot Access Services / Connection Refused:**
    *   Verify that your backend services are running and accessible on the local network.
    *   Ensure that the `target_url` in your `config.yml` or the `ingress` rules in your `cloudflared` configuration are correct.
    *   Check firewall rules that might be blocking connections between Moat and your backend services.
*   **Redirect Loops:**
    *   Verify `moat_base_url` in Moat's `config.yml` is **exactly** `https://moat.yourdomain.com` (or your equivalent).
    *   Check `X-Forwarded-Proto` and `X-Forwarded-Host` headers. Cloudflare tunnels generally set these correctly.
*   **Cookie Issues / Not Staying Logged In:**
    *   Ensure `cookie_domain` in Moat's `config.yml` is correct (e.g., `.yourdomain.com`).
    *   Check browser developer tools to see if cookies are being set for the correct domain.
*   **DNS Issues:** Ensure your DNS records created via `cloudflared tunnel route dns` have propagated. Use `dig` or `nslookup` for your public hostnames.

This detailed guide should help you get Moat up and running securely with Cloudflare Tunnel!