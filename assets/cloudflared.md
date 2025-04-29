# Setting Up Moat with Cloudflared (Cloudflare Tunnels)

**Conceptual Overview:**

1.  **Moat:** Runs on your local server (or inside a Docker container on that server), listening on a local port (e.g., `localhost:8000`). It handles authentication and reverse proxies requests to your backend services.
2.  **Backend Services:** These are your actual applications, running locally (e.g., `localhost:3001`, or as Docker containers like `http://my-app-container:80`). Moat needs to be able to reach these on the local network.
3.  **`cloudflared`:** A small daemon from Cloudflare that runs on the same server as Moat. It creates a secure, outbound-only connection to Cloudflare's edge network.
4.  **Cloudflare's Edge:** When a user accesses your public web application, the request goes through Cloudflare's network. Cloudflare then forwards the request to `cloudflared` on your server.
5.  **Secure Tunnel:** `cloudflared` then forwards the request to Moat. Moat authenticates the user and then reverse proxies the request to the appropriate backend service. The entire connection is secured by Cloudflare's tunnel.

**Steps:**

1.  **Install `cloudflared`:** Follow Cloudflare's instructions for installing `cloudflared` on your server.

2.  **Create a Tunnel:**

    ```bash
    cloudflared tunnel create <your-tunnel-name>
    ```

    This will generate a tunnel ID and a credentials file (`.json`). Store the tunnel ID as you'll need it later. The credentials file should be kept secret.

3.  **Configure DNS:** After creating the tunnel, Cloudflare will prompt you to create a DNS record. You can skip this step initially and configure the DNS records later, as described below.

4.  **Create a Configuration File:** Create a `config.yml` file for `cloudflared`. This file tells `cloudflared` how to route traffic.

    ```yaml
    tunnel: <your-tunnel-id>
    credentials-file: /path/to/<your-tunnel-id>.json

    ingress:
      - hostname: moat.yourdomain.com
        service: http://localhost:8000 # Moat's local address
      - hostname: app1.yourdomain.com
        service: http://localhost:3001 # Example backend service
      - hostname: app2.yourdomain.com
        service: http://my-app-container:80 # Example Docker container
      - service: http_status:404
    ```

    *   Replace `<your-tunnel-id>` with the actual tunnel ID.
    *   Replace `/path/to/<your-tunnel-id>.json` with the path to your credentials file.
    *   `moat.yourdomain.com` should point to your Moat instance.
    *   `app1.yourdomain.com` and `app2.yourdomain.com` are examples of how to route traffic to your backend services.  Ensure these hostnames match the `hostname` defined in Moat's static services or Docker labels.
    *   The `service: http_status:404` entry is a catch-all, returning a 404 error for any unmatched hostnames.

5.  **Run the Tunnel:**

    ```bash
    cloudflared tunnel run <your-tunnel-name>
    ```

    Alternatively, you can specify the config file:

    ```bash
    cloudflared tunnel --config /path/to/config.yml run
    ```

6.  **Configure DNS Records (Important):** Use the `cloudflared tunnel route dns` command to create the necessary DNS records in Cloudflare:

    ```bash
    cloudflared tunnel route dns <your-tunnel-name> moat.yourdomain.com
    cloudflared tunnel route dns <your-tunnel-name> app1.yourdomain.com
    cloudflared tunnel route dns <your-tunnel-name> app2.yourdomain.com
    ```

    This step is **crucial**. Without these DNS records, Cloudflare will not know where to send traffic for your hostnames.  If you skip this, you will likely get errors like "DNS PROBE FINISHED NXDOMAIN".

7.  **Configure Moat:** Ensure Moat's `config.yml` is configured correctly:

    *   `moat_base_url` should be set to your Moat's public URL via Cloudflare Tunnel (e.g., `https://moat.yourdomain.com`).
    *   `cookie_domain` should be set to your domain (e.g., `.yourdomain.com`).
    *   Static services and/or Docker labels should match the hostnames you're using in the Cloudflare Tunnel.

**Troubleshooting:**

*   **`DNS PROBE FINISHED NXDOMAIN`:** This almost always means you haven't properly configured the DNS records using `cloudflared tunnel route dns`.
*   **502/503 Errors:** These often indicate issues with the tunnel itself or the backend services. Check the `cloudflared` logs and ensure your backend services are running and accessible from the server where `cloudflared` is running.  Specifically, verify that `cloudflared` can reach Moat at `http://localhost:8000` (or whatever port you configured Moat to listen on).
*   **Moat Not Authenticating / Redirect Loops:** This usually means a misconfiguration of `moat_base_url` or `cookie_domain` in Moat's `config.yml`.  Also, verify that you've created DNS records for *all* services being proxied.
*   **Cloudflared Quits Unexpectedly:** Check the `cloudflared` logs for errors.  Common causes include invalid configuration files or issues with the Cloudflare tunnel itself.  Ensure the credentials file is valid and accessible.

**Important Considerations:**

*   **Security:** Cloudflare Tunnels provide a secure, outbound-only connection, which significantly enhances security.  You don't need to open any inbound ports on your server.
*   **HTTPS:** Cloudflare automatically handles HTTPS certificates for your domain, so you don't need to configure them on your server.
*   **Subdomains:** This setup works well with subdomains.  For example, you can have `moat.yourdomain.com` for Moat itself, `app1.yourdomain.com` for your first application, and so on.
*   **Docker:** If your backend services are running in Docker containers, make sure that Moat can reach them using their container names (e.g., `http://my-app-container:80`). You may need to create a Docker network that Moat and your backend containers share.  Alternatively, you can expose ports on the containers and access them via `localhost`.
*   **Logging:** Enable verbose logging in `cloudflared` to help diagnose issues. Use the `--loglevel debug` flag.

By following these steps, you can securely expose your self-hosted applications using Moat and Cloudflare Tunnel, without opening any inbound ports on your server. Remember to pay close attention to the DNS configuration and the settings in both Moat's and Cloudflare's configuration files. This setup centralizes authentication through Moat while benefiting from Cloudflare's security and performance features.

**Example Scenario:**

Let's say you have a Moat instance running on `localhost:8000`, and two applications:

*   `app1` running on `localhost:3001`
*   `app2` running in a Docker container named `my-app-container` on port 80.

You want to access these applications via the following URLs:

*   `https://moat.yourdomain.com`
*   `https://app1.yourdomain.com`
*   `https://app2.yourdomain.com`

Your `cloudflared` `config.yml` would look like this:

```yaml
tunnel: <your-tunnel-id>
credentials-file: /path/to/<your-tunnel-id>.json

ingress:
  - hostname: moat.yourdomain.com
    service: http://localhost:8000
  - hostname: app1.yourdomain.com
    service: http://localhost:3001
  - hostname: app2.yourdomain.com
    service: http://my-app-container:80
  - service: http_status:404
```

You would then run the following commands to create the DNS records:

```bash
cloudflared tunnel route dns <your-tunnel-name> moat.yourdomain.com
cloudflared tunnel route dns <your-tunnel-name> app1.yourdomain.com
cloudflared tunnel route dns <your-tunnel-name> app2.yourdomain.com
```

Finally, ensure your Moat configuration includes:

```yaml
moat_base_url: https://moat.yourdomain.com
cookie_domain: .yourdomain.com

static_services:
  - hostname: app1.yourdomain.com
    target_url: http://localhost:3001
```

And that your Docker container for `app2` has labels like:

```yaml
labels:
  moat.enable: "true"
  moat.hostname: "app2.yourdomain.com"
  moat.port: "80"
```

With this configuration, when a user accesses `https://app1.yourdomain.com`, Cloudflare will route the request to your server, `cloudflared` will forward it to Moat, Moat will authenticate the user, and then proxy the request to `localhost:3001`. The same process will occur for `https://app2.yourdomain.com`, but the request will be proxied to the `my-app-container` Docker container.  Unauthenticated users will be redirected to the Moat login page.

This detailed guide should help you get Moat up and running securely with Cloudflare Tunnel!