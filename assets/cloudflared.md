# Setting Up Moat with Cloudflared (Cloudflare Tunnels)

**Conceptual Overview:**

1.  **Moat:** Runs on your local server (or inside a Docker container on that server), listening on a local port (e.g., `localhost:8000`). It handles authentication and reverse proxies requests to your backend services.
2.  **Backend Services:** These are your actual applications, running locally (e.g., `localhost:3001`, or as Docker containers like `http://my-app-container:80`). Moat needs to be able to reach these on the local network.
3.  **`cloudflared`:** A small daemon from Cloudflare that runs on the same server as Moat. It creates a secure, outbound-only connection to Cloudflare's edge network.
4.  **Cloudflare's Edge:** When a user accesses your public website (e.g., `https://yourdomain.com`), Cloudflare's edge servers receive the request.

**Workflow:**

1.  User accesses `https://app.yourdomain.com`.
2.  Cloudflare's DNS directs the request to its edge network.
3.  The `cloudflared` daemon on your server intercepts the request and forwards it to Moat (e.g., `http://localhost:8000`).
4.  Moat authenticates the user. If successful, it proxies the request to the appropriate backend service (e.g., `http://localhost:3001`).
5.  The backend service processes the request and returns a response to Moat.
6.  Moat forwards the response back to `cloudflared`.
7.  `cloudflared` sends the response to Cloudflare's edge.
8.  Cloudflare's edge returns the response to the user.

**Prerequisites:**

*   A Cloudflare account.
*   A domain registered with Cloudflare.
*   `cloudflared` installed on your server.

**Steps:**

1.  **Install `cloudflared`:** Follow Cloudflare's instructions for installing `cloudflared` on your operating system.
2.  **Authenticate `cloudflared`:** Run `cloudflared login` and follow the prompts to authenticate with your Cloudflare account.
3.  **Create a Tunnel:**
    ```bash
    cloudflared tunnel create <tunnel-name>
    ```
    Replace `<tunnel-name>` with a name for your tunnel (e.g., `moat-tunnel`).  This will generate a Tunnel ID.
4.  **Create a Configuration File:** Create a `config.yml` file for `cloudflared` (e.g., in `/etc/cloudflared/config.yml`):

    ```yaml
    tunnel: <tunnel-id>
    credentials-file: /root/.cloudflared/<tunnel-id>.json
    ingress:
      - hostname: moat.yourdomain.com
        service: http://localhost:8000 # Moat's address
      - hostname: app1.yourdomain.com
        service: http://localhost:3001 # Your app
      - hostname: app2.yourdomain.com
        service: http://localhost:3002 # Another app
      - service: http_status:404
    ```

    *   Replace `<tunnel-id>` with the Tunnel ID from the previous step.
    *   Change `moat.yourdomain.com` to the desired hostname for your Moat instance.
    *   Set the `service` for `moat.yourdomain.com` to the address where Moat is listening (e.g., `http://localhost:8000`).
    *   Add additional `hostname` entries for each of your applications, pointing to their respective local addresses.
    *   The final `service: http_status:404` entry acts as a catch-all, returning a 404 error for any unmatched hostnames.
5.  **Create DNS Records:**  Use `cloudflared tunnel route dns` to create the necessary DNS records in Cloudflare:
    ```bash
    cloudflared tunnel route dns <tunnel-name> moat.yourdomain.com
    cloudflared tunnel route dns <tunnel-name> app1.yourdomain.com
    cloudflared tunnel route dns <tunnel-name> app2.yourdomain.com
    ```
    Replace `<tunnel-name>` and the hostnames with your actual values.
6.  **Run the Tunnel:**
    ```bash
    cloudflared tunnel run <tunnel-name>
    ```
    Or, to run in detached mode (as a service):
    ```bash
    cloudflared service install
    systemctl start cloudflared
    ```

**Important Considerations:**

*   **`moat_base_url`:** In Moat's `config.yml`, set `moat_base_url` to **exactly** match the public hostname you've assigned to Moat in Cloudflare (e.g., `https://moat.yourdomain.com`). This is crucial for correct redirects after login.
*   **Cookie Domain:**  Set `cookie_domain` in Moat's `config.yml` appropriately (e.g., `.yourdomain.com`) to ensure cookies are shared across your applications.
*   **HTTPS:** Cloudflare Tunnel provides automatic HTTPS encryption.  You do **not** need to configure HTTPS certificates on your local server.
*   **Security:** Cloudflare Tunnel creates outbound-only connections, enhancing security by eliminating the need to open inbound ports on your firewall.

**Troubleshooting:**

*   **Connectivity Issues:**
    *   Ensure `cloudflared` is running and properly configured. Check its logs for errors.
    *   Verify that your DNS records in Cloudflare are correctly pointing to the Cloudflare Tunnel.
    *   Confirm that Moat and your backend services are accessible from the server where `cloudflared` is running.  Use `curl` or `wget` to test.
*   **Proxying:**
    *   Double-check the `ingress` section of your `cloudflared` configuration file.  Ensure the hostnames and service addresses are correct.
    *   Verify that Moat is correctly configured to reverse proxy to your backend services.  Check Moat's logs for proxying errors.
*   **Redirect Loops:**
    *   Verify `moat_base_url` in Moat's `config.yml` is **exactly** `https://moat.yourdomain.com` (or your equivalent).
    *   Check `X-Forwarded-Proto` and `X-Forwarded-Host` headers. Cloudflare tunnels generally set these correctly.
*   **Cookie Issues / Not Staying Logged In:**
    *   Ensure `cookie_domain` in Moat's `config.yml` is correct (e.g., `.yourdomain.com`).
    *   Check browser developer tools to see if cookies are being set for the correct domain.
*   **DNS Issues:** Ensure your DNS records created via `cloudflared tunnel route dns` have propagated. Use `dig` or `nslookup` for your public hostnames.

This detailed guide should help you get Moat up and running securely with Cloudflare Tunnel!