# Setting Up Moat with Cloudflared (Cloudflare Tunnels)

**Conceptual Overview:**

1.  **Moat:** Runs on your local server (or inside a Docker container on that server), listening on a local port (e.g., `localhost:8000`). It handles authentication and reverse proxies requests to your backend services.
2.  **Backend Services:** These are your actual applications, running locally (e.g., `localhost:3001`, or as Docker containers like `http://my-app-container:80`). Moat needs to be able to reach these on the local network.
3.  **`cloudflared`:** A small daemon from Cloudflare that runs on the same server as Moat. It creates a secure, outbound-only connection to Cloudflare's edge network.
4.  **Cloudflare's Edge:** When a user accesses your public domain (e.g., `https://app.yourdomain.com`), Cloudflare's edge servers receive the request.
5.  **The Tunnel:** Cloudflare's edge forwards the request through the secure tunnel established by `cloudflared` to your Moat instance.

**Configuration Steps:**

1.  **Install `cloudflared`:** Follow Cloudflare's official documentation to install `cloudflared` on your server.

2.  **Create a Tunnel:**
    ```bash
    cloudflared tunnel create <your_tunnel_name>
    ```
    This will give you a Tunnel ID (UUID).

3.  **Create a Configuration File:**  `config.yml` for `cloudflared`.  This file tells `cloudflared` how to route traffic.  Example:

    ```yaml
    tunnel: <your_tunnel_id>
    credentials-file: /root/.cloudflared/<your_tunnel_id>.json

    ingress:
      - hostname: moat.yourdomain.com
        service: http://localhost:8000  # Moat's local address
      - hostname: app.yourdomain.com
        service: http://localhost:3001  # Example backend app
      - service: http_status:404
    ```

    *   Replace `<your_tunnel_id>` with the actual Tunnel ID.
    *   `moat.yourdomain.com` should point to your Moat instance.
    *   `app.yourdomain.com` is an example backend application.
    *   The final `service: http_status:404` is a catch-all, returning a 404 if no other route matches.

4.  **Route DNS Records:** Tell Cloudflare to send traffic for your hostnames to the tunnel.
    ```bash
    cloudflared tunnel route dns moat <your_tunnel_name> moat.yourdomain.com
    cloudflared tunnel route dns moat <your_tunnel_name> app.yourdomain.com
    ```
    Replace `<your_tunnel_name>` with your tunnel's name.

5.  **Run the Tunnel:**
    ```bash
    cloudflared tunnel run <your_tunnel_name>
    ```

6.  **Moat Configuration:**  Configure `moat_base_url` in Moat's `config.yml`.  This is **crucial** for correct redirecting and cookie handling.

    ```yaml
    moat_base_url: https://moat.yourdomain.com
    cookie_domain: .yourdomain.com  # Important for SSO
    ```

**Important Considerations & Troubleshooting:**

*   **HTTPS:** Cloudflare Tunnels provide encryption in transit. Moat should be configured to use HTTPS for cookie settings to work correctly. The `moat_base_url` **must** be `https://...`.  If you're running Moat locally without HTTPS, Cloudflare handles the encryption between the client and Cloudflare's edge.
*   **`moat_base_url`:** This setting tells Moat the public URL it's being accessed on. It's essential for generating correct redirect URLs after login and for setting cookies correctly.  If you access Moat via `https://moat.yourdomain.com`, `moat_base_url` **must** be set to `https://moat.yourdomain.com`.
*   **Cookie Domain:** Setting `cookie_domain` to `.yourdomain.com` enables SSO across all subdomains. If you only want cookies to apply to a specific subdomain (e.g., `moat.yourdomain.com`), set it accordingly.
*   **Local Ports:** Ensure `cloudflared` can access Moat and your backend services on the local network (e.g., `localhost:8000`).
*   **Health Checks:** Cloudflare can perform health checks on your tunnel endpoints. Configure these in the Cloudflare dashboard for added reliability.
*   **Multiple Tunnels:** You can create multiple tunnels for different applications or environments.
*   **Docker:** If Moat and your applications are running in Docker containers, ensure they are on the same network so `cloudflared` can reach them by container name (e.g., `http://my-app-container:8000`).
*   **`X-Forwarded-Proto`**: Cloudflare automatically sets the `X-Forwarded-Proto` header, indicating whether the original request was HTTP or HTTPS. Moat uses this to set cookie security correctly.
*   **Cloudflare Zero Trust:** Cloudflare Tunnel integrates with Cloudflare Zero Trust, allowing you to add additional security policies and access controls.

**Common Issues & Resolutions:**

*   **"The service is unavailable" (502/503 Errors):**
    *   Double-check that `cloudflared` is running.
    *   Verify that Moat is running and accessible on the local network (e.g., `localhost:8000`).
    *   Ensure your backend services are running and accessible to both Moat and `cloudflared`.
    *   Check Cloudflare's health checks for tunnel endpoints.
*   **"Too many redirects" or Redirect Loops:**
    *   This usually indicates an issue with `moat_base_url`. Ensure it is set correctly to your public Moat URL (e.g., `https://moat.yourdomain.com`).
    *   Check your Cloudflare Page Rules or other Cloudflare settings for conflicting redirects.
*   **Login Issues:**
    *   Clear your browser cookies for your domain.
    *   Ensure `cookie_domain` is configured correctly in Moat's `config.yml`.
    *   Verify that `moat_base_url` is set to `https://` if you're using HTTPS.
*   **DNS Propagation:** After creating DNS records in Cloudflare, allow time for propagation.

By following these steps and carefully configuring Cloudflare Tunnel and Moat, you can create a secure and reliable reverse proxy setup for your self-hosted applications. Remember to double-check your configurations and consult Cloudflare's documentation for the most up-to-date information. Using Cloudflare Tunnel allows you to expose your services without opening inbound ports on your server, improving security and simplifying network management. Cloudflare handles TLS termination and DDoS protection, offloading these tasks from your server. This setup is ideal for homelab enthusiasts and anyone wanting to securely expose self-hosted services. Always keep your `cloudflared` and Moat installations up to date for the latest security patches and features. Consider using a configuration management tool to automate the deployment and configuration of `cloudflared` and Moat. Always review Cloudflare's billing and usage policies to avoid unexpected charges. Cloudflare offers a free tier for basic usage, but more advanced features may require a paid plan. Thoroughly test your setup after making any changes to ensure everything is working as expected. Use browser developer tools to inspect network requests, cookies, and console messages for troubleshooting. Regularly monitor your Cloudflare dashboard for performance and security insights. Consider setting up alerts for critical events, such as tunnel outages or security threats. Cloudflare provides various tools for monitoring and managing your tunnels and DNS records. Take advantage of these tools to maintain a healthy and secure infrastructure. Experiment with different Cloudflare features to optimize your setup for performance and security. Cloudflare offers a wide range of options, so take the time to explore and find what works best for your needs.

This setup provides a secure and efficient way to access your self-hosted applications through Cloudflare's global network.

**Example `docker-compose.yml` for Moat with Cloudflared:**

```yaml
version: "3.9"
services:
  moat:
    image: ghcr.io/your-repo/moat:latest # Replace with your Moat image
    ports:
      - "8000:8000" # Expose port 8000 internally
    volumes:
      - ./config.yml:/app/config.yml # Mount your config file
    environment:
      - DATABASE_URL=sqlite+aiosqlite:////app/moat.db # Database path inside container
    restart: always
    networks:
      - cloudflare

  cloudflared:
    image: cloudflare/cloudflared:latest
    depends_on:
      - moat
    command: tunnel run
    environment:
      - TUNNEL_CREDENTIALS_FILE=/root/.cloudflared/<your_tunnel_id>.json #Mount the tunnel credentials file. Replace with your file
      - TUNNEL_CONFIG=/root/.cloudflared/config.yml  #Mount the cloudflared config file
    volumes:
      - ./cloudflared_config:/root/.cloudflared
    networks:
      - cloudflare

networks:
  cloudflare: # Add a network for cloudflared and moat to communicate
    name: cloudflare
```

**Example `cloudflared_config/config.yml` for cloudflared:**

```yaml
tunnel: <your_tunnel_id>
credentials-file: /root/.cloudflared/<your_tunnel_id>.json

ingress:
  - hostname: moat.yourdomain.com
    service: http://moat:8000  # Moat's internal address inside the Docker network
  - hostname: app.yourdomain.com
    service: http://your_app:3000  # Example backend app internal address inside the Docker network
  - service: http_status:404
```

Remember to replace placeholders with your actual values. This Docker Compose setup will deploy Moat and Cloudflared in a Docker environment, allowing you to access your services securely through Cloudflare Tunnel.

This should provide a very comprehensive guide to setting up Moat with Cloudflare tunnels!