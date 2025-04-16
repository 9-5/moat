# Setting Up Moat with Cloudflared (Cloudflare Tunnels)

**Conceptual Overview:**

1.  **Moat:** Runs on your local server (or inside a Docker container on that server), listening on a local port (e.g., `localhost:8000`). It handles authentication and reverse proxies requests to your backend services.
2.  **Backend Services:** These are your actual applications, running locally (e.g., `localhost:3001`, or as Docker containers like `http://my-app-container:80`). Moat needs to be able to reach these on the local network.
3.  **`cloudflared`:** A small daemon from Cloudflare that runs on the same server as Moat. It creates a secure, outbound-only connection to Cloudflare's edge network.
4.  **Cloudflare's Edge:** When a user accesses your publicly accessible hostname (e.g., `https://my-app.yourdomain.com`), Cloudflare's edge network receives the request. Because you've configured a Cloudflare Tunnel, Cloudflare knows to forward that request to your `cloudflared` daemon.
5.  **Secure Tunnel:** The `cloudflared` daemon forwards the request through the secure, outbound-only tunnel to Moat. Moat then authenticates the user (if necessary) and reverse proxies the request to your backend service.

**Prerequisites:**

*   A Cloudflare account and a domain name managed through Cloudflare.
*   `cloudflared` installed on your server (where Moat and your backend services are running).  See Cloudflare's documentation for installation instructions: [https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/)
*   Moat installed and configured (see main README for Moat setup).

**Steps:**

1.  **Create a Cloudflare Tunnel:**

    *   In your Cloudflare dashboard, navigate to "Tunnels" under the "Zero Trust" section.
    *   Click "Create a tunnel".
    *   Give your tunnel a name (e.g., "moat-tunnel").
    *   Choose an environment (e.g., "Linux").  Cloudflare will provide a command to install and run `cloudflared` with the tunnel's credentials.  Run this command on your server.

2.  **Configure DNS Records:**

    *   After creating the tunnel, you need to configure DNS records to route traffic through it.  You can do this using the `cloudflared tunnel route dns` command.
    *   For **each** service you want to expose through Moat and the tunnel, create a DNS record that points to the tunnel.  For example:

        ```bash
        cloudflared tunnel route dns my-tunnel app1.yourdomain.com
        cloudflared tunnel route dns my-tunnel app2.yourdomain.com
        cloudflared tunnel route dns my-tunnel moat.yourdomain.com # VERY IMPORTANT: Route your Moat instance itself!
        ```

        Replace `my-tunnel` with the name of your tunnel and `app1.yourdomain.com`, `app2.yourdomain.com`, and `moat.yourdomain.com` with the hostnames of your services and your Moat instance.  **Ensure you create a DNS record for Moat's hostname itself!**

3.  **Configure Moat:**

    *   **`moat_base_url`:**  In Moat's `config.yml`, set `moat_base_url` to the **public hostname** you are using to access Moat through the tunnel (e.g., `https://moat.yourdomain.com`).  This is **critical** for correct redirects after login.
    *   **`cookie_domain`:** Set `cookie_domain` in Moat's `config.yml` to match your domain (e.g., `.yourdomain.com`).  This ensures cookies are shared correctly across subdomains.
    *   **Target URLs:**  Make sure Moat can reach your backend services on your local network. If your services are running as Docker containers, ensure they are on the same Docker network as Moat, or that Moat can reach them via their IP addresses or hostnames.

4.  **Configure `cloudflared` (if needed):**

    *   In most cases, `cloudflared` will automatically detect services running on `localhost`.  However, if your services are running on different ports or IP addresses, you may need to create a `config.yml` file for `cloudflared` to define the routes explicitly.
    *   See Cloudflare's documentation for details: [https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/configuration/config-file/](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/configuration/config-file/)
    *   Example `cloudflared` config (usually located at `~/.cloudflared/config.yml`):

        ```yaml
        tunnel: <your-tunnel-id>
        credentials-file: /root/.cloudflared/<your-tunnel-id>.json

        ingress:
          - hostname: app1.yourdomain.com
            service: http://localhost:9001  # Assuming your app is on port 9001
          - hostname: app2.yourdomain.com
            service: http://localhost:9002  # Another app on port 9002
          - hostname: moat.yourdomain.com
            service: http://localhost:8000  # Moat is running on port 8000
          - service: http_status:404
        ```

        Replace `<your-tunnel-id>` with your actual tunnel ID and adjust the `service` URLs to match your backend applications. **The `moat.yourdomain.com` entry is essential!**

**Important Considerations:**

*   **HTTPS:** Cloudflare Tunnels provide automatic HTTPS encryption. You **do not** need to configure TLS certificates directly in Moat when using a tunnel.  Cloudflare handles the TLS termination.
*   **`moat_base_url` is Critical:**  Setting `moat_base_url` correctly is essential for Moat to function correctly behind a reverse proxy or tunnel.  It tells Moat the public URL it is being accessed at.
*   **Port 8000:** Ensure that port 8000 (or the port Moat is listening on) is **not** publicly exposed. The Cloudflare Tunnel provides the secure connection, so you don't need to open this port to the internet.
*   **Outbound-Only:** Cloudflare Tunnels are outbound-only connections. This significantly improves security because you don't need to open any inbound ports on your server.

**Troubleshooting:**

*   **"Tunnel connection refused"**:
    *   Ensure `cloudflared` is running and connected to Cloudflare.  Check the `cloudflared` logs.
    *   Verify the tunnel ID and credentials file are correct in the `cloudflared` configuration.
    *   Double-check that the DNS records are correctly pointing to the Cloudflare tunnel.  Use `dig` or `nslookup`.
*   **"Bad Gateway" errors:**
    *   Verify that Moat is running and accessible on the local network.
    *   Check that Moat can reach your backend services.
    *   Examine Moat's logs for errors while proxying.
    *   Double-check your `cloudflared` configuration to ensure the correct `service` URLs are being used.
*   **Authentication Issues / Redirect Loops:**
    *   This is almost always a `moat_base_url` misconfiguration. Verify `moat_base_url` in Moat's `config.yml` is **exactly** `https://moat.yourdomain.com` (or your equivalent).
    *   Clear your browser's cookies for your domain to ensure there are no conflicting cookies.
*   **Cookie Issues / Not Staying Logged In:**
    *   Ensure `cookie_domain` in Moat's `config.yml` is correct (e.g., `.yourdomain.com`).
    *   Check browser developer tools to see if cookies are being set for the correct domain.
*   **DNS Issues:** Ensure your DNS records created via `cloudflared tunnel route dns` have propagated. Use `dig` or `nslookup` for your public hostnames.

This detailed guide should help you get Moat up and running securely with Cloudflare Tunnel!