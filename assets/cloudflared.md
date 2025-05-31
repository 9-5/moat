# Setting Up Moat with Cloudflared (Cloudflare Tunnels)

**Conceptual Overview:**

1.  **Moat:** Runs on your local server (or inside a Docker container on that server), listening on a local port (e.g., `localhost:8000`). It handles authentication and reverse proxies requests to your backend services.
2.  **Backend Services:** These are your actual applications, running locally (e.g., `localhost:3001`, or as Docker containers like `http://my-app-container:80`). Moat needs to be able to reach these on the local network.
3.  **`cloudflared`:** A small daemon from Cloudflare that runs on the same server as Moat. It creates a secure, outbound-only connection to Cloudflare's edge network.
4.  **Cloudflare's Edge:** When a user accesses your publicly accessible hostname (e.g., `app.yourdomain.com`), Cloudflare's edge network receives the request.  You configure a DNS record to point to Cloudflare.
5.  **The Tunnel:** Cloudflare, using the tunnel created by `cloudflared`, forwards the request to your `cloudflared` instance.  `cloudflared` then forwards the request to Moat.  Moat authenticates the user.  If authenticated, Moat reverse proxies the request to your backend service.

**Prerequisites:**

*   A Cloudflare account and a domain name managed through Cloudflare.
*   `cloudflared` installed on the same server as your Moat instance.
*   Moat installed and configured.

**Steps:**

1.  **Install and Authenticate `cloudflared`:**

    *   Follow Cloudflare's official documentation to install `cloudflared` on your server:  [https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/)
    *   Authenticate `cloudflared` with your Cloudflare account using `cloudflared login`.  This will open a browser window for you to log in and select your domain.

2.  **Create a Tunnel:**

    *   Create a new tunnel using `cloudflared tunnel create <tunnel-name>`. Replace `<tunnel-name>` with a descriptive name for your tunnel.
    *   Note the tunnel ID (UUID) that `cloudflared` outputs.  You'll need this later.

3.  **Configure the Tunnel:**

    *   Create a `config.yml` file for `cloudflared` (typically located in `~/.cloudflared/config.yml` or `/etc/cloudflared/config.yml`).  This file defines how `cloudflared` routes traffic.

    ```yaml
    tunnel: <tunnel-id> # Replace with your tunnel ID
    credentials-file: /root/.cloudflared/<tunnel-id>.json # Replace with the correct path
    ingress:
      - hostname: app.yourdomain.com  # Replace with the public hostname for your app
        service: http://localhost:8000   # Moat's address (adjust port if needed)
      - hostname: test.yourdomain.com  # Replace with another hostname
        service: http://localhost:8000   # Pointing to Moat again
      - service: http_status:404 # Default to 404 if no route matches
    ```

    *   **Important Considerations for `service`:**
        *   All hostnames should proxy through Moat.
        *   Moat, in turn, proxies to your backend services based on the *Host* header.
        *   Therefore, every hostname you want to protect with Moat should point to Moat's address.
        *   **Do NOT point `cloudflared` directly to your backend services!** MOAT handles the reverse proxying after authenticating the user.

4.  **Route Traffic to the Tunnel:**

    *   Use `cloudflared tunnel route dns <tunnel-id> <hostname>` to create DNS records in Cloudflare that point your hostnames to the tunnel.
        *   For example: `cloudflared tunnel route dns <tunnel-id> app.yourdomain.com`
        *   Repeat this for each hostname you want to route through the tunnel.

5.  **Run the Tunnel:**

    *   Start the tunnel with `cloudflared tunnel run <tunnel-name>`.

6.  **Configure Moat:**

    *   Ensure your Moat `config.yml` has the following settings configured correctly:

        *   `moat_base_url`: This **must** be set to the public URL where Moat is accessible through the Cloudflare Tunnel (e.g., `https://moat.yourdomain.com`).  This is crucial for redirects after login.
        *   `cookie_domain`:  Set this to your domain (e.g., `.yourdomain.com`) for SSO to work correctly across subdomains.

**Troubleshooting:**

*   **502 or 504 Errors:**
    *   Check that `cloudflared` is running and connected.
    *   Verify that Moat is running and accessible from the server where `cloudflared` is running (e.g., `curl http://localhost:8000`).
    *   Ensure that your backend services are running and accessible from Moat.
*   **Ensure that the hostnames in your `cloudflared` config.yml file point to MOAT, not directly to your backend services.** MOAT is responsible for authentication and reverse proxying.
*   **Redirect Loops:**
    *   Verify `moat_base_url` in Moat's `config.yml` is **exactly** `https://moat.yourdomain.com` (or your equivalent).
    *   Check `X-Forwarded-Proto` and `X-Forwarded-Host` headers. Cloudflare tunnels generally set these correctly.
*   **Cookie Issues / Not Staying Logged In:**
    *   Ensure `cookie_domain` in Moat's `config.yml` is correct (e.g., `.yourdomain.com`).
    *   Check browser developer tools to see if cookies are being set for the correct domain.
*   **DNS Issues:** Ensure your DNS records created via `cloudflared tunnel route dns` have propagated. Use `dig` or `nslookup` for your public hostnames.

This detailed guide should help you get Moat up and running securely with Cloudflare Tunnel!