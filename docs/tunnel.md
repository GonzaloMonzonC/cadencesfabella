# Exposing the web console (optional)

The web console (`:8087`) is handy from your phone. This guide is deliberately
generic — substitute your own domain and tunnel provider.

> Rule of thumb: the console can **read your Saved Messages and send as you**.
> Treat its URL as a secret. Always keep the token (`X-Fabella-Token`) enabled,
> and preferably put an identity layer (SSO / access policies) in front.

## Example: Cloudflare Tunnel

1. Install `cloudflared` and authenticate:

   ```bash
   cloudflared tunnel login
   ```

2. Create a tunnel and route a hostname to it:

   ```bash
   cloudflared tunnel create fabella
   cloudflared tunnel route dns fabella console.example.com
   ```

3. Point the tunnel at the console (`config.yml`):

   ```yaml
   tunnel: fabella
   credentials-file: ~/.cloudflared/<tunnel-id>.json
   ingress:
     - hostname: console.example.com
       service: http://localhost:8087
     - service: http_status:404
   ```

4. Run it:

   ```bash
   cloudflared tunnel run fabella
   ```

5. *(Recommended)* Protect `console.example.com` with an access policy so only
   your identity gets through — and keep the CadencesFaBela token as a second layer.

## What NOT to do

- Don't expose `:8086` (the Bot API port) to the internet — it is meant to be
  local.
- Don't run a public console without the token, and without understanding that
  the console acts **as your account**.
