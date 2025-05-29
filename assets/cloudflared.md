# Setting Up Moat with Cloudflared (Cloudflare Tunnels)

**Conceptual Overview:**

1.  **Moat:** Runs on your local server (or inside a Docker container on that server), listening on a local port (e.g., `localhost:8000`). It handles authentication and reverse proxies requests to your backend services.
2.  **Backend Services:** These are your actual applications, running locally (e.g., `localhost:3001`, or as Docker containers like `http://my-app-container:80`). Moat needs to be able to reach these on the local network.
3.  **`cloudflared`:** A small daemon from Cloudflare that runs on the same server as Moat. It creates a secure, outbound-only connection to Cloudflare's edge network.
4.  **Cloudflare's Edge:** When a user accesses your public hostname (e.g., `https://my-app.yourdomain.com`), Cloudflare's edge servers receive the request. Because you've configured a tunnel, Cloudflare knows to forward the request through the `cloudflared` daemon on your server.
5.  **The Tunnel:** `cloudflared` receives the request, and forwards it to Moat (e.g., `localhost:8000`). Moat authenticates the user.  If successful, it reverse proxies the request to your backend service (e.g., `http://my-app-container:80`).
6.  **The Response:** The response from the backend service travels back through Moat, `cloudflared`, Cloudflare's edge, and finally to the user's browser.

**Prerequisites:**

*   A Cloudflare account and a domain name managed through Cloudflare.
*   Moat installed and configured on your server.
*   `cloudflared` installed on the same server as Moat.  See Cloudflare's documentation for installation instructions: [https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/)

**Steps:**

1.  **Create a Cloudflare Tunnel:**

    *   In your Cloudflare dashboard, navigate to "Zero Trust" -> "Access" -> "Tunnels".
    *   Click "Create a tunnel".
    *   Give your tunnel a name (e.g., "moat-tunnel").
    *   Choose an environment (e.g., "Linux").
    *   Follow the instructions to install and run `cloudflared` on your server.  This typically involves running a command like:

        ```bash
        cloudflared service install --token <YOUR_TUNNEL_TOKEN>
        ```

        Replace `<YOUR_TUNNEL_TOKEN>` with the token provided by Cloudflare.

2.  **Configure DNS Records:**

    *   After creating the tunnel, you need to route traffic to it.  You'll use `cloudflared tunnel route dns` commands to create DNS records in Cloudflare that point to your tunnel.

    *   **Route Moat Itself:**  First, create a DNS record for Moat's base URL (e.g., `moat.yourdomain.com`).  This ensures users can access the Moat login page.

        ```bash
        cloudflared tunnel route dns <YOUR_TUNNEL_ID> moat.yourdomain.com
        ```

        Replace `<YOUR_TUNNEL_ID>` with the ID of your tunnel (found in the Cloudflare dashboard). Replace `moat.yourdomain.com` with the `moat_base_url` you've configured in Moat's `config.yml`.

    *   **Route Backend Services:** For each backend service you want to protect with Moat, create a DNS record that points to the tunnel.  For example, if you have a service `app1.yourdomain.com` that you want to protect:

        ```bash
        cloudflared tunnel route dns <YOUR_TUNNEL_ID> app1.yourdomain.com
        ```

3.  **Configure Ingress Rules (Important!)**

    *   This is the **most important** step!  You need to tell `cloudflared` how to route traffic *internally* to Moat.  Create a YAML file (e.g., `config.yml`) for `cloudflared` with the following content:

        ```yaml
        tunnel: <YOUR_TUNNEL_ID>
        credentials-file: /root/.cloudflared/<YOUR_TUNNEL_ID>.json

        ingress:
          - hostname: moat.yourdomain.com # Or whatever your moat_base_url is
            service: http://localhost:8000  # Moat's local address
          - hostname: app1.yourdomain.com # Example backend service
            service: http://localhost:8000 # Proxy THROUGH Moat
          - service: http_status:404 # Default rule - return 404 for anything not matched
        ```

        **Explanation:**

        *   `tunnel`: Your Tunnel ID.
        *   `credentials-file`: Path to the credentials file created when you set up the tunnel.
        *   `ingress`:  A list of rules that define how traffic is routed.
            *   `hostname`: The public hostname.
            *   `service`:  The internal address where `cloudflared` should forward the traffic.  **Crucially, all traffic goes *through* Moat (http://localhost:8000).** Moat then decides, based on authentication, whether to proxy the request to the actual backend.
            *   `http_status:404`: A catch-all rule that returns a 404 error for any hostname that doesn't match a defined rule.  This is a good security practice.

    *   **Important:**  The `hostname` values in the `cloudflared` config **must** match the hostnames you used in the `cloudflared tunnel route dns` commands and in your Moat configuration.

    *   Run `cloudflared` with the config file:

        ```bash
        cloudflared tunnel run --config config.yml
        ```

4.  **Configure Moat:**

    *   In Moat's `config.yml`:
        *   Set `moat_base_url` to `https://moat.yourdomain.com` (or your equivalent).  This is essential for redirects to work correctly.
        *   Set `cookie_domain` to `.yourdomain.com` if your applications are on subdomains.
        *   Ensure your static service or Docker labels are configured to use the same hostnames (e.g., `app1.yourdomain.com`).  Moat needs to know which hostnames to protect.

**Example Scenario:**

Let's say you have the following:

*   Domain: `yourdomain.com`
*   Moat `moat_base_url`: `https://moat.yourdomain.com`
*   Application: `https://app1.yourdomain.com` running on `http://localhost:3001`

Your configurations would look like this:

*   **Cloudflare DNS:**
    *   `moat.yourdomain.com`  CNAME pointing to your Cloudflare tunnel.
    *   `app1.yourdomain.com` CNAME pointing to your Cloudflare tunnel.

*   **`cloudflared` config.yml:**

    ```yaml
    tunnel: <YOUR_TUNNEL_ID>
    credentials-file: /root/.cloudflared/<YOUR_TUNNEL_ID>.json

    ingress:
      - hostname: moat.yourdomain.com
        service: http://localhost:8000
      - hostname: app1.yourdomain.com
        service: http://localhost:8000
      - service: http_status:404
    ```

*   **Moat config.yml:**

    ```yaml
    listen_host: 0.0.0.0
    listen_port: 8000
    secret_key: "..."
    moat_base_url: https://moat.yourdomain.com
    cookie_domain: .yourdomain.com
    static_services:
      - hostname: app1.yourdomain.com
        target_url: http://localhost:3001
    ```

**Troubleshooting:**

*   **Cloudflared Connection Issues:**
    *   Check `cloudflared` logs for errors. Ensure it's properly connected to Cloudflare.
    *   Verify the tunnel ID and credentials file path in the `cloudflared` config.yml.
*   **Moat Not Authenticating / Redirect Loops:**
    *   Double-check that `moat_base_url` in Moat's `config.yml` is **exactly** the same as the hostname you're using to access Moat through Cloudflare.
    *   Ensure the `hostname` values in `cloudflared`'s `ingress` match the hostnames in Cloudflare DNS and Moat's configuration.
*   **Backend Service Not Accessible:**
    *   Make sure Moat can reach your backend service at the `target_url` you've configured. Test this by accessing the `target_url` directly from the server where Moat is running (e.g., using `curl`).
    *   Ensure the `service` entry in `cloudflared`'s `ingress` for your backend service points to `http://localhost:8000` (Moat's address), not directly to the backend.  Traffic must flow through Moat for authentication and proxying.
*   **502/504 Errors:** These often indicate a problem with the connection between `cloudflared` and Moat, or between Moat and the backend service.  Check logs for both.
*   **"Too Many Redirects" Error:** This usually means there's a redirect loop.  Double-check your `moat_base_url` and ensure that all hostnames are configured correctly in Cloudflare, `cloudflared`, and Moat.

**Advanced Configuration:**

*   **Using Argo Tunnel:**  For improved performance and security, consider using Cloudflare's Argo Tunnel feature.  This provides a persistent connection between `cloudflared` and Cloudflare's edge.  See Cloudflare's documentation for details.
*   **Load Balancing:**  If you have multiple instances of your backend service, you can configure Cloudflare to load balance traffic across them.  See Cloudflare's documentation for load balancing.
*   **Access Policies:** Cloudflare Access allows you to define more granular access policies for your applications.  You can use Access to require users to authenticate with specific identity providers (e.g., Google, GitHub) before being allowed to access your applications.  However, if you are using MOAT, you would typically rely on MOAT for authentication and reverse proxying.
*   **Health Checks:** Configure health checks in Cloudflare to monitor the health of your `cloudflared` tunnels and your backend services.

By following these steps, you can securely expose your self-hosted applications to the internet using Moat and Cloudflare Tunnel. Remember to pay close attention to the hostname configurations and ensure that traffic flows through Moat for authentication and proxying.

This detailed guide should help you get Moat up and running securely with Cloudflare Tunnel!