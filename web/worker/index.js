// The AI endpoint for the browser build, and the only place the Anthropic
// API key exists.
//
// Cloudflare Access sits in front of /api/ai and checks each caller's
// service token. This Worker then verifies the signed JWT Access attaches,
// so a request that reached it some other way (a workers.dev or preview
// URL, or an Access app that was edited or removed) is still refused.
//
// The browser only supplies the conversation text. Model, system prompt and
// token limit come from assistant.generated.json, which web/build.py writes
// from rtk/assistant, so credentials cannot be used for anything else.

import Anthropic from "@anthropic-ai/sdk";
import { createRemoteJWKSet, jwtVerify } from "jose";

import assistant from "./assistant.generated.json";

const ENDPOINT = "/api/ai";
const MAX_BODY_CHARS = 512 * 1024;

function reply(status, body) {
  return Response.json(body, {
    status,
    headers: { "cache-control": "no-store" },
  });
}

// Kept between requests so the signing keys are not fetched every time.
let accessKeys = null;

function keysFor(teamDomain) {
  if (accessKeys === null) {
    const url = new URL(`${teamDomain}/cdn-cgi/access/certs`);
    accessKeys = createRemoteJWKSet(url);
  }
  return accessKeys;
}

async function approvedByAccess(request, env) {
  const token = request.headers.get("cf-access-jwt-assertion");
  if (!token) {
    return false;
  }
  try {
    await jwtVerify(token, keysFor(env.TEAM_DOMAIN), {
      issuer: env.TEAM_DOMAIN,
      audience: env.POLICY_AUD,
      algorithms: ["RS256"],
    });
    return true;
  } catch {
    return false;
  }
}

// Return the messages if they are a plain text conversation, else null.
// Plain strings only: no images, documents or tool blocks on this key.
function readMessages(text) {
  let body;
  try {
    body = JSON.parse(text);
  } catch {
    return null;
  }
  const messages = body?.messages;
  if (!Array.isArray(messages) || messages.length === 0) {
    return null;
  }
  const valid = messages.every(
    (message, index) =>
      message?.role === (index % 2 === 0 ? "user" : "assistant") &&
      typeof message.content === "string" &&
      message.content.length > 0,
  );
  if (!valid || messages.at(-1).role !== "user") {
    return null;
  }
  return messages.map(({ role, content }) => ({ role, content }));
}

async function chat(request, env) {
  const text = await request.text();
  if (text.length > MAX_BODY_CHARS) {
    return reply(413, { error: "Conversation too long." });
  }
  const messages = readMessages(text);
  if (messages === null) {
    return reply(400, { error: "Expected a plain text conversation." });
  }

  const client = new Anthropic({
    apiKey: env.ANTHROPIC_API_KEY,
    baseURL: env.ANTHROPIC_BASE_URL,
  });
  try {
    // awaited here so a failed request becomes a status code rather than
    // a broken stream
    const stream = await client.messages.create({
      model: assistant.model,
      max_tokens: assistant.max_tokens,
      system: assistant.system,
      output_config: { effort: assistant.effort },
      messages,
      stream: true,
    });
    return new Response(stream.toReadableStream(), {
      headers: {
        "content-type": "application/x-ndjson",
        "cache-control": "no-store",
      },
    });
  } catch (err) {
    if (err instanceof Anthropic.RateLimitError) {
      return reply(429, { error: "Rate limit hit." });
    }
    // Never 401/403: those mean "Access said no" to the terminal, and a
    // problem with the API key must not lock out a valid user.
    console.error("Anthropic request failed", err?.status, err?.message);
    return reply(502, { error: `AI service error (${err?.status ?? "?"}).` });
  }
}

export default {
  async fetch(request, env) {
    if (new URL(request.url).pathname !== ENDPOINT) {
      return reply(404, { error: "Not found." });
    }
    if (!env.TEAM_DOMAIN || !env.POLICY_AUD || !env.ANTHROPIC_API_KEY) {
      return reply(503, { error: "The AI endpoint is not configured." });
    }
    if (!(await approvedByAccess(request, env))) {
      return reply(403, { error: "Not approved by Cloudflare Access." });
    }

    if (request.method === "GET") {
      // reaching this line is the approval the terminal is asking for
      return reply(200, { ok: true });
    }
    if (request.method === "POST") {
      return chat(request, env);
    }
    return reply(405, { error: "Method not allowed." });
  },
};
