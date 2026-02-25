/**
 * GDPR DSAR demo — uses the TypeScript SDK server-side, exactly like the
 * Rust TUI uses the Rust SDK.  No browser proxy, no CORS.
 *
 * Usage:
 *   node cookbook/gdpr-dsar-compliance/serve.js
 *
 * Environment variables:
 *   AI_SDK_HOST     (default: http://localhost:8585)
 *   AI_SDK_TOKEN    (default: dev JWT)
 *   AI_SDK_AGENT    (default: GDPRComplianceAnalyzer)
 *   PORT            (default: 8080)
 */

import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { join, extname } from "node:path";
import { fileURLToPath } from "node:url";
import { AISdk } from "@openmetadata/ai-sdk";

const HOST = (process.env.AI_SDK_HOST || "http://localhost:8585").replace(/\/$/, "");
const TOKEN =
  process.env.AI_SDK_TOKEN ||
  "eyJraWQiOiJHYjM4OWEtOWY3Ni1nZGpzLWE5MmotMDI0MmJrOTQzNTYiLCJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJhZG1pbiIsImlzQm90IjpmYWxzZSwiaXNzIjoib3Blbi1tZXRhZGF0YS5vcmciLCJpYXQiOjE2NjM5Mzg0NjIsImVtYWlsIjoiYWRtaW5Ab3Blbm1ldGFkYXRhLm9yZyJ9.tS8um_5DKu7HgzGBzS1VTA5uUjKWOCU0B_j08WXBiEC0mr0zNREkqVfwFDD-d24HlNEbrqioLsBuFRiwIWKc1m_ZlVQbG7P36RUxhuv2vbSp80FKyNM-Tj93FDzq91jsyNmsQhyNv_fNr3TXfzzSPjHt8Go0FMMP66weoKMgW2PbXlhVKwEuXUHyakLLzewm9UMeQaEiRzhiTMU3UkLXcKbYEJJvfNFcLwSl9W8JCO_l0Yj3ud-qt_nQYEZwqW6u5nfdQllN133iikV4fM5QZsMCnm8Rq1mvLR0y9bmJiD7fwM1tmJ791TUWqmKaTnP49U493VanKpUAfzIiOiIbhg";
const AGENT_NAME = process.env.AI_SDK_AGENT || "GDPRComplianceAnalyzer";
const PORT = parseInt(process.env.PORT || "8080", 10);
const DIR = fileURLToPath(new URL(".", import.meta.url));
const MIME = { ".html": "text/html", ".js": "text/javascript" };

// ── SDK client (same pattern as the Rust TUI) ──────────────────────
const client = new AISdk({ host: HOST, token: TOKEN });
const agent = client.agent(AGENT_NAME);

// ── Multi-turn settings ─────────────────────────────────────────────
// Each invoke() is one backend turn. The agent often needs several
// turns: search → inspect details → trace lineage → compile report.
// We keep invoking with the same conversationId until the agent
// produces a response that looks like a finished report.
const MAX_TURNS = 8;
const CONTINUE = "Continue.";

/** True when the response looks like the agent is mid-workflow and
 *  wants to keep going (e.g. "Let me get details…", "Now I'll trace…"). */
function needsContinuation(text) {
  const t = text.trimEnd();
  // Ends with colon — agent is about to list/do something
  if (t.endsWith(":")) return true;
  // Ends mid-sentence with a continuation signal
  if (/\b(let me|now I'll|I'll now|next,? I)\b[^.!]*$/i.test(t)) return true;
  // Used tools but response has no markdown headers — still narrating
  if (t.length > 0 && !t.includes("##") && !t.includes("| ")) return true;
  return false;
}

createServer(async (req, res) => {
  // ── POST /api/analyze — multi-turn invoke, return JSON ────────────
  if (req.method === "POST" && req.url === "/api/analyze") {
    try {
      const chunks = [];
      for await (const chunk of req) chunks.push(chunk);
      const { message } = JSON.parse(Buffer.concat(chunks).toString());

      console.log(`\n[turn 1] Invoking agent "${AGENT_NAME}"...`);
      let result = await agent.invoke(message);
      let convId = result.conversationId;
      const allTools = [...result.toolsUsed];
      let bestResponse = result.response;

      console.log(`  → ${result.response.length} chars, tools: ${result.toolsUsed.join(", ") || "none"}`);

      // The agent's workflow spans multiple turns. Keep invoking with
      // the same conversationId until the response looks like a
      // finished report (has markdown structure, doesn't end mid-thought).
      let turn = 1;
      while (needsContinuation(bestResponse) && turn < MAX_TURNS && convId) {
        turn++;
        console.log(`[turn ${turn}] Agent still working — continuing conversation...`);
        result = await agent.invoke(CONTINUE, { conversationId: convId });
        convId = result.conversationId;
        allTools.push(...result.toolsUsed);
        // The latest turn's response usually supersedes — the agent
        // builds on prior context. Keep whichever is longer.
        if (result.response.length > bestResponse.length) {
          bestResponse = result.response;
        }
        console.log(`  → ${result.response.length} chars, tools: ${result.toolsUsed.join(", ") || "none"}`);
      }

      console.log(`Done — ${turn} turn(s), ${bestResponse.length} chars total`);

      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({
        response: bestResponse,
        toolsUsed: [...new Set(allTools)],
      }));
    } catch (err) {
      console.error("Agent error:", err.message);
      const status = err.statusCode || 502;
      res.writeHead(status, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: err.message }));
    }
    return;
  }

  // ── Static files ──────────────────────────────────────────────────
  const file = join(DIR, req.url === "/" ? "index.html" : req.url);
  readFile(file)
    .then((buf) => {
      res.writeHead(200, { "Content-Type": MIME[extname(file)] || "application/octet-stream" });
      res.end(buf);
    })
    .catch(() => { res.writeHead(404); res.end("Not found"); });
}).listen(PORT, () => {
  console.log(`GDPR DSAR demo → http://localhost:${PORT}`);
  console.log(`SDK client: ${AGENT_NAME} @ ${HOST}`);
});
