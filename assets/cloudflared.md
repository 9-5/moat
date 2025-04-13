# Setting Up Moat with Cloudflared (Cloudflare Tunnels)

**Conceptual Overview:**

1.  **Moat:** Runs on your local server (or inside a Docker container on that server), listening on a local port (e.g., `localhost:8000`). It handles authentication and reverse proxies requests to your backend services.
2.  **Backend Services:** These are your actual applications, running locally (e.g., `localhost:3001`, or as Docker containers like `http://my-app-container:80`). Moat needs to be able to reach these on the local network.
3.  **`cloudflared`:** A small daemon from Cloudflare that runs on the same server as Moat. It creates a secure, outbound-only connection to Cloudflare's edge network.
4.  **Cloudflare's Edge:** When a user accesses your public hostname (e.g., `https://app.yourdomain.com`), Cloudflare's edge servers receive the request.  The tunnel forwards that request securely to your server running Moat.

**Configuration Steps:**

1.  **Install `cloudflared`:** Follow Cloudflare's official documentation to install `cloudflared` on your server.

2.  **Authenticate `cloudflared`:** Run `cloudflared tunnel login` and authenticate with your Cloudflare account. This will authorize `cloudflared` to create tunnels for your zones.

3.  **Create a Tunnel:**
    ```bash
    cloudflared tunnel create <your-tunnel-name>
    ```
    This command creates a tunnel in your Cloudflare account. Note the tunnel ID that's outputted.

4.  **Create a Configuration File:** Create a `config.yml` file for `cloudflared`. This file tells `cloudflared` how to route traffic.  A minimal example:
    ```yaml
    tunnel: <your-tunnel-id>
    credentials-file: /root/.cloudflared/<your-tunnel-id>.json  # Adjust path
    ingress:
      - hostname: moat.yourdomain.com  # Your Moat hostname
        service: http://localhost:8000   # Moat's local address
      - service: http_status:404  # Default fallback
    ```
    *   **`tunnel`:**  The ID of the tunnel you created.
    *   **`credentials-file`:** Path to the credentials file for your tunnel.
    *   **`ingress`:** Defines how traffic is routed.  The first entry routes traffic for `moat.yourdomain.com` to Moat running locally.  The second entry is a catch-all, returning a 404 for any unmatched requests.  **Adjust hostnames and service URLs to match your setup.**

5.  **Route Traffic:** Use `cloudflared tunnel route dns` to create DNS records in Cloudflare that point to your tunnel.
    ```bash
    cloudflared tunnel route dns <your-tunnel-name> moat.yourdomain.com
    ```
    This creates a CNAME record for `moat.yourdomain.com` that points to your Cloudflare tunnel.  Repeat this command for each hostname you want to route through the tunnel.

6.  **Run the Tunnel:** Start the tunnel with:
    ```bash
    cloudflared tunnel run <your-tunnel-name>
    ```
    Keep this running in a terminal or use a service manager like `systemd` to run it in the background.

7.  **Configure Moat:** In Moat's `config.yml` file:
    *   Set `moat_base_url` to your public hostname (e.g., `https://moat.yourdomain.com`). **This is crucial!**
    *   Set `cookie_domain` to your domain (e.g., `.yourdomain.com`).

**Important Considerations & Troubleshooting:**

*   **HTTPS:** Cloudflare tunnels handle HTTPS termination at the edge. Your traffic between Cloudflare and your origin server can be either HTTP or HTTPS. For simplicity and performance, using HTTP (as shown in the examples) is often sufficient, as the tunnel itself is encrypted.
*   **Origin CA Certificates (Optional):** For enhanced security, you can use Cloudflare's Origin CA certificates to encrypt traffic between Cloudflare and your origin server. This adds another layer of encryption on top of the tunnel's security, but is generally not required.
*   **Subdomains:** You can use subdomains to route traffic to different services. For example, `app1.yourdomain.com` could point to one service, and `app2.yourdomain.com` to another, all proxied through Moat. Ensure your `cloudflared` config file and Moat's configuration (static services or Docker labels) are correctly configured for each subdomain.
*   **Redirect Loops:**
    *   Verify `moat_base_url` in Moat's `config.yml` is **exactly** `https://moat.yourdomain.com` (or your equivalent).
    *   Check `X-Forwarded-Proto` and `X-Forwarded-Host` headers. Cloudflare tunnels generally set these correctly.
*   **Cookie Issues / Not Staying Logged In:**
    *   Ensure `cookie_domain` in Moat's `config.yml` is correct (e.g., `.yourdomain.com`).
    *   Check browser developer tools to see if cookies are being set for the correct domain.
*   **DNS Issues:** Ensure your DNS records created via `cloudflared tunnel route dns` have propagated. Use `dig` or `nslookup` for your public hostnames.

This detailed guide should help you get Moat up and running securely with Cloudflare Tunnel!