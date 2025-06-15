# Setting Up Moat with Cloudflared (Cloudflare Tunnels)

**Conceptual Overview:**

1.  **Moat:** Runs on your local server (or inside a Docker container on that server), listening on a local port (e.g., `localhost:8000`). It handles authentication and reverse proxies requests to your backend services.
2.  **Backend Services:** These are your actual applications, running locally (e.g., `localhost:3001`, or as Docker containers like `http://my-app-container:80`). Moat needs to be able to reach these on the local network.
3.  **`cloudflared`:** A small daemon from Cloudflare that runs on the same server as Moat. It creates a secure, outbound-only connection to Cloudflare's edge network.
4.  **Cloudflare's Edge:** When a user accesses your public domain (e.g., `moat.yourdomain.com` or `app1.yourdomain.com`), Cloudflare routes this request through the secure tunnel to your `cloudflared` daemon, which then forwards it to Moat.

## Prerequisites:

1.  **Cloudflare Account:** You need a free or paid Cloudflare account.
2.  **Domain on Cloudflare:** Your domain (e.g., `yourdomain.com`) must be managed by Cloudflare (i.e., its nameservers pointing to Cloudflare).
3.  **Moat Installed & Running Locally:** Ensure Moat is installed, configured with a `secret_key` and an admin user, and can run (e.g., `python -m moat.main run`). For now, `moat_base_url` can be `http://localhost:8000`.
4.  **`cloudflared` CLI:** The command-line tool for Cloudflare Tunnel.

## Step 1: Install `cloudflared`

Download and install the `cloudflared` daemon on the server where Moat will run.
Instructions are here: [https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/)

Choose the package or binary appropriate for your OS (Linux, macOS, Windows).
For example, on Linux (Debian/Ubuntu):
```bash
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb
```
Or for other systems, download the binary and place it in your `PATH`.

## Step 2: Authenticate `cloudflared`

Log in `cloudflared` to your Cloudflare account. This will create a certificate file that `cloudflared` uses to create tunnels for your account.
```bash
cloudflared login
```
This will open a browser window asking you to log in to Cloudflare and authorize the domain you want to use with the tunnel. Select your desired domain.

Upon successful login, `cloudflared` will download a `cert.pem` file, usually stored in `~/.cloudflared/cert.pem` (Linux/macOS) or `%USERPROFILE%\.cloudflared\cert.pem` (Windows).

## Step 3: Create a Tunnel

A Tunnel is a persistent connection between your server and Cloudflare's edge.
```bash
cloudflared tunnel create moat-tunnel
```
Replace `moat-tunnel` with a descriptive name for your tunnel.
This command will output:
*   A **Tunnel ID** (a UUID). **Save this ID.**
*   The path to a **credentials file** for this tunnel (e.g., `~/.cloudflared/<TUNNEL_ID>.json`). This file contains the tunnel's secret.

## Step 4: Configure `cloudflared` (Ingress Rules)

You need to tell `cloudflared` which public hostnames should be routed through this tunnel and to which local services they should point. All traffic for Moat-protected services will go *to Moat's local endpoint*.

Create a configuration file for `cloudflared`, often named `config.yml` (this is **different** from Moat's `config.yml`). A common location is `~/.cloudflared/config.yml` or `/etc/cloudflared/config.yml` if running as a system service.

**`cloudflared` Configuration (`~/.cloudflared/config.yml` or similar):**
```yaml
# Tunnel UUID or Name (using the name is often easier)
tunnel: moat-tunnel # Or use the TUNNEL_ID from Step 3

# Path to the tunnel credentials file created in Step 3
credentials-file: /home/your_user/.cloudflared/<YOUR_TUNNEL_ID>.json # Adjust path as needed!
                  # On Linux, if running as root service: /root/.cloudflared/<YOUR_TUNNEL_ID>.json

# Ingress rules define how public hostnames are routed to local services
ingress:
  # Rule 1: Moat's own public interface
  - hostname: moat.yourdomain.com  # The public URL for Moat's UI and auth
    service: http://localhost:8000 # Where Moat is listening locally

  # Rule 2: A service protected by Moat
  - hostname: app1.yourdomain.com  # Public URL for your first app
    service: http://localhost:8000 # TRAFFIC FOR THIS ALSO GOES TO MOAT

  # Rule 3: Another service protected by Moat
  - hostname: app2.yourdomain.com  # Public URL for your second app
    service: http://localhost:8000 # TRAFFIC FOR THIS ALSO GOES TO MOAT

  # Add more hostname entries for every public FQDN Moat will serve.
  # ALL of them will point to Moat's local service (e.g., http://localhost:8000).
  # Moat itself will then look at the incoming Host header (app1.yourdomain.com)
  # and proxy to the correct backend based on its own static_services or Docker labels.

  # Catch-all rule: MUST be the last rule
  - service: http_status:404
```

**Explanation of `cloudflared` config:**

*   `tunnel`: The name or ID of the tunnel you created.
*   `credentials-file`: **Crucial!** Point this to the `.json` credentials file generated when you created the tunnel. The path varies based on user and OS.
*   `ingress`: A list of routing rules.
    *   `hostname`: The public FQDN that users will type in their browser.
    *   `service`: The local URL that `cloudflared` should forward requests for that hostname to. **For all hostnames that Moat will handle, this `service` will be Moat's listening address (e.g., `http://localhost:8000`).**
*   `service: http_status:404`: This is a required catch-all rule. It should be the last rule in the `ingress` list.

## Step 5: Create DNS Records for Your Hostnames via `cloudflared`

Now, you need to create CNAME DNS records in Cloudflare that point your public hostnames to your tunnel. `cloudflared` can manage this for you.

For each `hostname` defined in your `cloudflared` `config.yml`'s `ingress` section:
```bash
cloudflared tunnel route dns moat-tunnel moat.yourdomain.com
cloudflared tunnel route dns moat-tunnel app1.yourdomain.com
cloudflared tunnel route dns moat-tunnel app2.yourdomain.com
# ... and so on for all other hostnames
```
Replace `moat-tunnel` with your tunnel's name or ID, and `moat.yourdomain.com`, etc., with your actual hostnames.

This command tells Cloudflare that when it receives a request for `moat.yourdomain.com`, it should route it through `moat-tunnel`.

## Step 6: Configure Moat (`config.yml` for Moat)

Now, adjust Moat's own `config.yml` to be aware of its public-facing URL and cookie domain.

**Moat's `config.yml`:**
```yaml
listen_host: "0.0.0.0" # Or "localhost" / "127.0.0.1"
listen_port: 8000      # The port cloudflared's 'service' points to

secret_key: "YOUR_VERY_SECRET_KEY_CHANGE_THIS_NOW_PLEASE"
access_token_expire_minutes: 60
database_url: "sqlite+aiosqlite:///./moat.db"

# CRITICAL for Cloudflared setup:
moat_base_url: "https://moat.yourdomain.com" # Public HTTPS URL of Moat itself
cookie_domain: ".yourdomain.com"             # For SSO across subdomains

# Docker monitor settings (if you use it)
docker_monitor_enabled: true
moat_label_prefix: "moat"

static_services:
  - hostname: "app1.yourdomain.com" # Public hostname Moat listens for
    target_url: "http://localhost:3001" # LOCAL target for app1
  - hostname: "app2.yourdomain.com"
    target_url: "http://localhost:3002" # LOCAL target for app2
  # Or if app2 is a Docker container on a shared network with Moat (if Moat is also containerized):
  # - hostname: "app2.yourdomain.com"
  #   target_url: "http://app2-container-name:8080"
```

**Key changes in Moat's `config.yml`:**

*   `moat_base_url`: **This is extremely important.** It MUST be the public HTTPS URL that users will use to access Moat's login page, as defined in your `cloudflared` config (e.g., `https://moat.yourdomain.com`). Moat uses this for redirects.
*   `cookie_domain`: Set this to your parent domain with a leading dot (e.g., `.yourdomain.com`) if you want Single Sign-On (SSO) to work across `moat.yourdomain.com`, `app1.yourdomain.com`, etc.
*   `static_services` or Docker labels:
    *   `hostname`: These are the **public hostnames** (e.g., `app1.yourdomain.com`). These must match the hostnames you configured in `cloudflared`'s ingress rules (which all point their `service` to Moat's local port).
    *   `target_url`: How Moat reaches the backend service **locally** (e.g., `http://localhost:3001`, or if using Docker with Moat in a container, perhaps `http://my-app-container:internal_port`).

## Step 7: Run `cloudflared` Tunnel

You can run the tunnel manually first to test:
```bash
cloudflared tunnel --config /home/your_user/.cloudflared/config.yml run
# Adjust --config path if your cloudflared config.yml is elsewhere
```
If you didn't use a `cloudflared` `config.yml` for ingress rules (and only used `cloudflared tunnel route dns`), you might run it by its name or ID directly:
```bash
# cloudflared tunnel run moat-tunnel # This usually expects ingress rules in Zero Trust Dashboard.
# Using a config file for ingress is generally more explicit for self-hosted cloudflared.
```
You should see `cloudflared` connect to Cloudflare's edge servers.

**To run `cloudflared` as a service (recommended for production):**
```bash
sudo cloudflared service install
# This may require the cloudflared config.yml to be in a system location like /etc/cloudflared/
# The service install command might also take the tunnel token directly if not using a full config file.
# Refer to `cloudflared service --help` and official docs for specifics on your OS.
# For example, it might copy your ~/.cloudflared/config.yml to /etc/cloudflared/config.yml
# Ensure the credentials file path inside the system config.yml is correct for the user
# the service will run as (often root).
sudo systemctl enable cloudflared
sudo systemctl start cloudflared
sudo systemctl status cloudflared # To check its running
```

## Step 8: Run Moat

In a separate terminal (or as its own service):
```bash
python -m moat.main run
```

## Step 9: Testing

1.  **Access Moat UI:** Open your browser and go to `https://moat.yourdomain.com`. You should see Moat's login page (served over HTTPS via Cloudflare).
2.  **Login:** Log in with your Moat admin user.
3.  **Access Admin UI:** You should be redirected to Moat's admin UI at `https://moat.yourdomain.com/moat/admin/config`.
4.  **Access a Protected Service:** Go to `https://app1.yourdomain.com`.
    *   If you weren't logged in via `moat.yourdomain.com` first, you should be redirected to `https://moat.yourdomain.com/moat/auth/login?redirect_uri=https://app1.yourdomain.com`.
    *   After logging in, you should be redirected back to `https://app1.yourdomain.com` and see your application, proxied by Moat.
5.  **Test Docker Dynamic Services (if configured):**
    *   Start a Docker container with the correct labels (e.g., `moat.enable="true"`, `moat.hostname="dockerapp.yourdomain.com"`, `moat.port="container_port"`).
    *   Add `dockerapp.yourdomain.com` to your `cloudflared` `config.yml`'s ingress section, pointing its `service` to `http://localhost:8000` (Moat's local endpoint).
    *   Run `cloudflared tunnel route dns moat-tunnel dockerapp.yourdomain.com`.
    *   Restart `cloudflared` if you modified its `config.yml` (if not running as a service that auto-reloads, or `sudo systemctl restart cloudflared`).
    *   Moat should detect the Docker service.
    *   Access `https://dockerapp.yourdomain.com`. You should be authenticated by Moat and then see the Dockerized application.

## Security & Best Practices:

*   **Cloudflare Access:** For an additional layer of security, you can configure Cloudflare Access policies in the Cloudflare Zero Trust dashboard to protect your hostnames even before traffic reaches Moat. This can add MFA, device posture checks, etc.
*   **HTTPS Mode:** In your Cloudflare SSL/TLS settings for your domain, ensure it's set to "Full (Strict)" for maximum security. This means Cloudflare encrypts traffic to `cloudflared`, and `cloudflared` expects a valid certificate if your local service (Moat) were HTTPS (though we configured `service: http://localhost:8000`). For `http://localhost`, "Full" is sufficient, but "Full (Strict)" is best practice generally.
*   **Firewall:** With `cloudflared`, you do *not* need to open any inbound ports on your server's firewall for Moat or your backend applications. All connections are outbound from `cloudflared`.
*   **Keep `cloudflared` Updated:** Regularly update the `cloudflared` daemon.

## Troubleshooting:

*   **502/503 Errors:**
    *   Check `cloudflared` logs: `journalctl -u cloudflared -f` (if running as a service) or its console output.
    *   Is `cloudflared` running and connected?
    *   Is Moat running and listening on the correct local port specified in `cloudflared`'s `service` directive?
    *   Can `cloudflared` reach Moat locally (e.g., `curl http://localhost:8000` from the server itself)?
*   **Moat Logs:** Check Moat's console output for errors related to configuration, authentication, or proxying.
*   **Redirect Loops:**
    *   Verify `moat_base_url` in Moat's `config.yml` is **exactly** `https://moat.yourdomain.com` (or your equivalent).
    *   Check `X-Forwarded-Proto` and `X-Forwarded-Host` headers. Cloudflare tunnels generally set these correctly.
*   **Cookie Issues / Not Staying Logged In:**
    *   Ensure `cookie_domain` in Moat's `config.yml` is correct (e.g., `.yourdomain.com`).
    *   Check browser developer tools to see if cookies are being set for the correct domain.
*   **DNS Issues:** Ensure your DNS records created via `cloudflared tunnel route dns` have propagated. Use `dig` or `nslookup` for your public hostnames.

This detailed guide should help you get Moat up and running securely with Cloudflare Tunnel!