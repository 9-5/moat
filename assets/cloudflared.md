# Setting Up Moat with Cloudflared (Cloudflare Tunnels)

**Conceptual Overview:**

1.  **Moat:** Runs on your local server (or inside a Docker container on that server), listening on a local port (e.g., `localhost:8000`). It handles authentication and reverse proxies requests to your backend services.
2.  **Backend Services:** These are your actual applications, running locally (e.g., `localhost:3001`, or as Docker containers like `http://my-app-container:80`). Moat needs to be able to reach these on the local network.
3.  **`cloudflared`:** A small daemon from Cloudflare that runs on the same server as Moat. It creates a secure, outbound-only connection to Cloudflare's edge network.
4.  **Cloudflare's Edge:** When a user accesses your publicly accessible domain (e.g., `yourdomain.com`), Cloudflare's edge servers receive the request.
5.  **The Tunnel:** Cloudflare's edge forwards the request through the secure tunnel established by `cloudflared` to your Moat instance.
6.  **Moat's Role:** Moat authenticates the user. If authenticated, it then reverse proxies the request to the appropriate backend service on your local network.

**Steps:**

1.  **Install `cloudflared`:** Follow Cloudflare's official instructions to install `cloudflared` on your server.

    *   [https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/)

2.  **Authenticate `cloudflared` with Cloudflare:**

    ```bash
    cloudflared tunnel login
    ```

    This will open a browser window to authenticate with your Cloudflare account.  Choose the domain you want to use for the tunnel.

3.  **Create a Tunnel:**

    ```bash
    cloudflared tunnel create <tunnel_name>
    ```

    Replace `<tunnel_name>` with a descriptive name (e.g., `moat-tunnel`).  This command creates a tunnel on Cloudflare's side and generates a tunnel ID.  It also creates a `credentials.json` file in the `~/.cloudflared/<tunnel_name>.json` which contains the tunnel's credentials.  **Keep this file safe!**

4.  **Create a Configuration File (`config.yml`) for `cloudflared`:**

    Create a `config.yml` file in the `~/.cloudflared/` directory (create the directory if it doesn't exist).  This file tells `cloudflared` how to route traffic.  A minimal example:

    ```yaml
    tunnel: <tunnel_id>
    credentials-file: /root/.cloudflared/<tunnel_name>.json

    ingress:
      - hostname: moat.yourdomain.com  # Replace with your Moat's public hostname
        service: http://localhost:8000   # Moat's local address and port
      - hostname: app1.yourdomain.com  # Example app behind Moat
        service: http://localhost:3001  # Example app's local address and port
      - hostname: app2.yourdomain.com
        service: http://localhost:3002
      - service: http_status:404 # Catch-all

    ```

    *   **`tunnel`:**  The tunnel ID generated in step 3.
    *   **`credentials-file`:**  The path to the `credentials.json` file.
    *   **`ingress`:**  Defines the routing rules.  Each entry maps a hostname to a local service.
        *   **`hostname`:** The public hostname you want to use.
        *   **`service`:**  The local address (usually `http://localhost:<port>`) of the service.  For Moat, this should be Moat's `listen_port`.  For applications behind Moat, this should be the application's local address.
    *   **Important:** The order of the `ingress` rules matters. The last rule (the catch-all) should always be `service: http_status:404`

5.  **Create DNS Records (Important!)**

    After creating the tunnel, you need to tell Cloudflare to route traffic for your chosen hostnames through the tunnel.  Use the `cloudflared tunnel route dns` command:

    ```bash
    cloudflared tunnel route dns <tunnel_name> moat.yourdomain.com
    cloudflared tunnel route dns <tunnel_name> app1.yourdomain.com
    cloudflared tunnel route dns <tunnel_name> app2.yourdomain.com
    ```

    Replace `<tunnel_name>` with your tunnel's name and `moat.yourdomain.com`, `app1.yourdomain.com`, etc. with the hostnames you configured in your `config.yml`.  This command creates CNAME records in your Cloudflare DNS settings that point to the tunnel.

6.  **Run the Tunnel:**

    ```bash
    cloudflared tunnel run <tunnel_name>
    ```

    This starts the `cloudflared` daemon and establishes the connection to Cloudflare.  You should see output indicating that the tunnel is running and connected.

7.  **Configure Moat (`config.yml`)**

    *   **`moat_base_url`:** Set this to the **exact** public URL you're using for Moat (e.g., `https://moat.yourdomain.com`). This is **critical** for correct redirects after login.
    *   **`cookie_domain`:**  Set this to your domain (e.g., `.yourdomain.com`) so that cookies work correctly across all your subdomains.

**Example Scenario:**

*   You have a domain: `yourdomain.com`
*   You want to access Moat at: `https://moat.yourdomain.com`
*   You have two applications:
    *   `app1` running on `localhost:3001` accessible via `https://app1.yourdomain.com`
    *   `app2` running on `localhost:3002` accessible via `https://app2.yourdomain.com`

Your `cloudflared` `config.yml` would look like:

```yaml
tunnel: <your_tunnel_id>
credentials-file: /root/.cloudflared/<your_tunnel_name>.json

ingress:
  - hostname: moat.yourdomain.com
    service: http://localhost:8000
  - hostname: app1.yourdomain.com
    service: http://localhost:3001
  - hostname: app2.yourdomain.com
    service: http://localhost:3002
  - service: http_status:404
```

You would then run these commands:

```bash
cloudflared tunnel route dns <your_tunnel_name> moat.yourdomain.com
cloudflared tunnel route dns <your_tunnel_name> app1.yourdomain.com
cloudflared tunnel route dns <your_tunnel_name> app2.yourdomain.com
```

And your Moat `config.yml` would include:

```yaml
moat_base_url: https://moat.yourdomain.com
cookie_domain: .yourdomain.com
```

**Important Considerations:**

*   **Security:** Cloudflare Tunnel provides a secure, outbound-only connection.  No inbound ports need to be opened on your server.
*   **HTTPS:** Cloudflare handles the HTTPS termination.  Moat and your applications only need to communicate over HTTP internally.
*   **DNS Propagation:**  It can take some time for DNS records to propagate after creating them.

**Troubleshooting:**

*   **`cloudflared` not running:** Check the `cloudflared` logs for errors. Ensure the `config.yml` is correctly formatted and the tunnel ID and credentials file are valid.
*   **Moat not accessible:**
    *   Verify `cloudflared` is running and connected.
    *   Check the `cloudflared` logs for routing errors.
    *   Ensure your DNS records are correctly configured and have propagated.
    *   Double-check that `moat.yourdomain.com` (or your equivalent) is correctly set up in Cloudflare's DNS settings and is associated with the tunnel.
*   **Applications not accessible:**
    *   Verify that the applications are running locally and accessible from the server where `cloudflared` is running.
    *   Check the `cloudflared` logs for errors when routing to the applications.
    *   Ensure the hostnames and service addresses in your `cloudflared` `config.yml` are correct.
*   **Redirect Loops:**
    *   Verify `moat_base_url` in Moat's `config.yml` is **exactly** `https://moat.yourdomain.com` (or your equivalent).
    *   Check `X-Forwarded-Proto` and `X-Forwarded-Host` headers. Cloudflare tunnels generally set these correctly.
*   **Cookie Issues / Not Staying Logged In:**
    *   Ensure `cookie_domain` in Moat's `config.yml` is correct (e.g., `.yourdomain.com`).
    *   Check browser developer tools to see if cookies are being set for the correct domain.
*   **DNS Issues:** Ensure your DNS records created via `cloudflared tunnel route dns` have propagated. Use `dig` or `nslookup` for your public hostnames.

This detailed guide should help you get Moat up and running securely with Cloudflare Tunnel!