# Setting Up Moat with Cloudflared (Cloudflare Tunnels)

**Conceptual Overview:**

1.  **Moat:** Runs on your local server (or inside a Docker container on that server), listening on a local port (e.g., `localhost:8000`). It handles authentication and reverse proxies requests to your backend services.
2.  **Backend Services:** These are your actual applications, running locally (e.g., `localhost:3001`, or as Docker containers like `http://my-app-container:80`). Moat needs to be able to reach these on the local network.
3.  **`cloudflared`:** A small daemon from Cloudflare that runs on the same server as Moat. It creates a secure, outbound-only connection to Cloudflare's edge network.
4.  **Cloudflare's Edge:** When a user accesses your public hostname (e.g., `app1.example.com`), Cloudflare's edge servers route the request through the tunnel to `cloudflared`.
5.  **The Tunnel:** `cloudflared` forwards the request to Moat.
6.  **Authentication & Proxying:** Moat authenticates the user. If authenticated, it proxies the request to the appropriate backend service.
7.  **Response:** The response from the backend service travels back through Moat, `cloudflared`, and Cloudflare to the user.

**Configuration Steps:**

1.  **Install `cloudflared`:** Follow Cloudflare's official instructions for installing `cloudflared` on your server.  See: [https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/)

2.  **Create a Cloudflare Tunnel:**

    ```bash
    cloudflared tunnel create your-tunnel-name
    ```

3.  **Obtain Tunnel Credentials:**  After creating the tunnel, `cloudflared` will generate a credentials file (usually in `~/.cloudflared/`).  Note the path to this file; you'll need it later.

4.  **Create a Configuration File:**  Create a `config.yml` file for `cloudflared` (e.g., `/etc/cloudflared/config.yml`).  This file defines how `cloudflared` routes traffic.

    ```yaml
    tunnel: your-tunnel-id  # Replace with your tunnel ID
    credentials-file: /root/.cloudflared/your-tunnel-id.json # Replace with the path to your credentials file

    ingress:
      - hostname: moat.example.com # Replace with your Moat's public hostname
        service: http://localhost:8000  # Moat's local address
      - hostname: app1.example.com  # Replace with your app's public hostname
        service: http://localhost:3001  # Your app's local address (Moat will proxy to this)
      - hostname: app2.example.com
        service: http://localhost:3002
      - service: http_status:404  # Default to 404 if no route matches
    ```

    **Important:** Replace `your-tunnel-id`, the credential file path, `moat.example.com`, `app1.example.com`, and the service addresses with your actual values.  Ensure Moat's hostname points to `http://localhost:8000` (or the port Moat is listening on).  The other hostnames should be configured in Moat to point to your backend services.

5.  **Route Traffic with DNS Records:** Use the following command to create the necessary DNS records in Cloudflare.

    ```bash
    cloudflared tunnel route dns your-tunnel-id moat.example.com
    cloudflared tunnel route dns your-tunnel-id app1.example.com
    cloudflared tunnel route dns your-tunnel-id app2.example.com
    ```

    Replace `your-tunnel-id`, `moat.example.com`, `app1.example.com` and `app2.example.com` with your tunnel ID and desired hostnames. These commands tell Cloudflare's DNS to direct traffic for these hostnames to your tunnel.

6.  **Run the Tunnel:**

    ```bash
    cloudflared tunnel run your-tunnel-id
    ```

    Alternatively, you can run the tunnel as a service (recommended for production).  See Cloudflare's documentation for instructions on setting up a service: [https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/run-tunnel/run-as-a-managed-service/](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/run-tunnel/run-as-a-managed-service/)

7.  **Configure Moat:**

    *   Set `moat_base_url` in Moat's `config.yml` to the public hostname you're using for Moat (e.g., `https://moat.example.com`).
    *   Set `cookie_domain` to the base domain (e.g., `.example.com`) to enable SSO across subdomains.
    *   Ensure your backend applications are configured as static services or via Docker labels within Moat, pointing to their *internal* addresses (e.g., `http://localhost:3001`).

    For example:

    Cloudflare Tunnel `config.yml`:

    ```yaml
    tunnel: <your_tunnel_id>
    credentials-file: /root/.cloudflared/<your_tunnel_id>.json

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

**Troubleshooting:**

*   **Tunnel Not Connecting:**
    *   Check `cloudflared` logs for errors (usually in `/var/log/cloudflared/`).
    *   Verify the tunnel ID and credentials file path in `cloudflared`'s `config.yml`.
    *   Ensure `cloudflared` has permission to access the credentials file.
*   **Moat Not Accessible:**
    *   Verify `cloudflared` is routing traffic to Moat's local address (usually `http://localhost:8000`).
    *   Check Moat's logs for errors related to reverse proxying.
*   **Redirect Loops:**
    *   Verify `moat_base_url` in Moat's `config.yml` is **exactly** `https://moat.yourdomain.com` (or your equivalent).
    *   Check `X-Forwarded-Proto` and `X-Forwarded-Host` headers. Cloudflare tunnels generally set these correctly.
*   **Cookie Issues / Not Staying Logged In:**
    *   Ensure `cookie_domain` in Moat's `config.yml` is correct (e.g., `.yourdomain.com`).
    *   Check browser developer tools to see if cookies are being set for the correct domain.
*   **DNS Issues:** Ensure your DNS records created via `cloudflared tunnel route dns` have propagated. Use `dig` or `nslookup` for your public hostnames.

This detailed guide should help you get Moat up and running securely with Cloudflare Tunnel!