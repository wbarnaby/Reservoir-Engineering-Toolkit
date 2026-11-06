# Web build and the AI endpoint

The site is static files plus one Worker route, `/api/ai`. The Worker holds
the Anthropic API key. Nobody can reach it without a Cloudflare Access
service token.

```
terminal in browser  --CF-Access-Client-Id / -Secret-->  Cloudflare Access
                                                               |  checks the token, adds a signed JWT
                                                               v
                                                         Worker (web/worker/index.js)
                                                               |  verifies the JWT, adds the API key
                                                               v
                                                         Anthropic API
```

In the terminal, type `ai`, then the Client ID, then the Client Secret
(masked). The terminal asks Access to approve them before AI mode opens, and
sends them with every message after that. They stay in memory only, so a
page reload asks again.

The desktop app (`python -m rtk`) is unchanged and still uses your own API
key.

## One-time setup

Do these in order. Until all of it is done the terminal says the AI service
is not set up, or rejects the credentials, so nothing is exposed along the
way.

### 1. Create the Access application

In the Cloudflare dashboard, go to Zero Trust > Access controls > Applications
and add a self-hosted application:

- Domain: `rtk.willbarnaby.com`, path `api/ai`. Only this path. The rest of
  the site stays public.
- Policy: action **Service Auth** (not Allow, which would send callers to a
  login page), including the service tokens below.

Then copy the **Application Audience (AUD) Tag** from the application's
settings. You also need your team domain, which looks like
`https://<team-name>.cloudflareaccess.com`, with no trailing slash.

If your Zero Trust settings offer strict service token authentication, turn
it on. Access then answers failures with 401 or 403 and never issues a
session cookie. The terminal is safe either way: it sends no cookies and
follows no redirects.

### 2. Create one service token per person

In Zero Trust > Access controls > Service credentials, create a service token
for each person, named after them. The Client Secret is shown only once. Give
that person the Client ID and Client Secret, and add the token to the policy
from step 1.

### 3. Give the Worker its three secrets

```bash
npx wrangler secret put ANTHROPIC_API_KEY
```

```bash
npx wrangler secret put TEAM_DOMAIN
```

```bash
npx wrangler secret put POLICY_AUD
```

Keep the API key in its own Anthropic workspace with a monthly spend limit.
That limit is the real ceiling on what the tokens can cost you, because the
Worker has no per-person quota.

### 4. Deploy

The deploy needs both toolchains, in this order:

```bash
npm ci
```

```bash
python web/build.py
```

```bash
npx wrangler deploy
```

`web/build.py` writes `web/worker/assistant.generated.json`, and the deploy
fails without it. If Cloudflare builds this for you, make sure its build
command includes `npm ci` and `python web/build.py`.

## Managing access

- **Remove someone:** delete their service token. Their next message is
  rejected and the terminal locks. "Revoke existing tokens" on the application
  is not enough, because it only ends sessions.
- **Tokens expire** on the duration set when they were created. Use Refresh in
  the dashboard to extend one.
- **Change the model, effort or token limit:** edit `rtk/assistant/config.py`
  and redeploy. The system prompt is in `rtk/assistant/prompt.py`. The Worker
  gets all of these at build time and ignores anything the browser sends
  except the conversation text.

## Why the Worker checks the JWT as well

An Access application protects `rtk.willbarnaby.com`. Other addresses for the
same Worker, such as `workers.dev` and preview URLs, are not part of it.
`wrangler.jsonc` turns those off, and the Worker also refuses any request
without a valid Access JWT for this application. If the Access application is
ever edited or removed, the endpoint closes instead of opening your API key to
the internet.
