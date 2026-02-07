/**
 * GDPR DSAR demo — uses the TypeScript SDK server-side, exactly like the
 * Rust TUI uses the Rust SDK.  No browser proxy, no CORS.
 *
 * Usage:
 *   node cookbook/gdpr-dsar-compliance/serve.js
 *
 * Environment variables:
 *   METADATA_HOST   (default: http://localhost:8585)
 *   METADATA_TOKEN  (default: dev JWT)
 *   METADATA_AGENT  (default: GDPRComplianceAnalyzer)
 *   PORT            (default: 8080)
 */

import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { join, extname } from "node:path";
import { fileURLToPath } from "node:url";
import { MetadataAI } from "./metadata-ai.js";

const HOST = (process.env.METADATA_HOST || "http://localhost:8585").replace(/\/$/, "");
const TOKEN =
  process.env.METADATA_TOKEN ||
  "eyJraWQiOiJHYjM4OWEtOWY3Ni1nZGpzLWE5MmotMDI0MmJrOTQzNTYiLCJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJhZG1pbiIsImlzQm90IjpmYWxzZSwiaXNzIjoib3Blbi1tZXRhZGF0YS5vcmciLCJpYXQiOjE2NjM5Mzg0NjIsImVtYWlsIjoiYWRtaW5Ab3Blbm1ldGFkYXRhLm9yZyJ9.tS8um_5DKu7HgzGBzS1VTA5uUjKWOCU0B_j08WXBiEC0mr0zNREkqVfwFDD-d24HlNEbrqioLsBuFRiwIWKc1m_ZlVQbG7P36RUxhuv2vbSp80FKyNM-Tj93FDzq91jsyNmsQhyNv_fNr3TXfzzSPjHt8Go0FMMP66weoKMgW2PbXlhVKwEuXUHyakLLzewm9UMeQaEiRzhiTMU3UkLXcKbYEJJvfNFcLwSl9W8JCO_l0Yj3ud-qt_nQYEZwqW6u5nfdQllN133iikV4fM5QZsMCnm8Rq1mvLR0y9bmJiD7fwM1tmJ791TUWqmKaTnP49U493VanKpUAfzIiOiIbhg";
const AGENT_NAME = process.env.METADATA_AGENT || "GDPRComplianceAnalyzer";
const PORT = parseInt(process.env.PORT || "8080", 10);
const DIR = fileURLToPath(new URL(".", import.meta.url));
const MIME = { ".html": "text/html", ".js": "text/javascript" };

// ── SDK client (same pattern as the Rust TUI) ──────────────────────
const client = new MetadataAI({ host: HOST, token: TOKEN });
const agent = client.agent(AGENT_NAME);

// A real report is at least this long; anything shorter is the agent
// narrating intermediate steps ("Let me get details on…").
const MIN_REPORT_LEN = 500;
const MAX_TURNS = 4;
const NUDGE =
  "Stop searching. Compile ALL findings into the full GDPR compliance " +
  "report now — affected tables, PII columns, retention conflicts, " +
  "deletion order, and risk flags. Output markdown.";

/** Stream one turn, return { text, tools, conversationId }. */
async function streamOnce(message, conversationId) {
  let text = "";
  const tools = [];
  let convId = conversationId;
  for await (const ev of agent.stream(message, { conversationId })) {
    switch (ev.type) {
      case "content":
        if (ev.content) text += ev.content;
        break;
      case "tool_use":
        if (ev.toolName) tools.push(ev.toolName);
        break;
      case "error":
        throw new Error(ev.error || "Agent error");
    }
    if (ev.conversationId) convId = ev.conversationId;
  }
  return { text, tools, conversationId: convId };
}

createServer(async (req, res) => {
  // ── POST /api/analyze — stream via SDK, accumulate, return ────────
  if (req.method === "POST" && req.url === "/api/analyze") {
    try {
      const chunks = [];
      for await (const chunk of req) chunks.push(chunk);
      const { message } = JSON.parse(Buffer.concat(chunks).toString());

      // First turn — the user's actual DSAR request.
      let result = await streamOnce(message, undefined);
      let best = result.text;
      const allTools = [...result.tools];

      // If the agent stopped early with a narration line, continue the
      // conversation (like a TUI user would type "continue").
      let turn = 0;
      while (best.length < MIN_REPORT_LEN && turn < MAX_TURNS && result.conversationId) {
        turn++;
        console.log(`  turn ${turn}: ${best.length} chars — nudging agent to produce report`);
        result = await streamOnce(NUDGE, result.conversationId);
        allTools.push(...result.tools);
        // Keep the longest response (the actual report).
        if (result.text.length > best.length) best = result.text;
      }

      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ response: best, toolsUsed: [...new Set(allTools)] }));
    } catch (err) {
      if (!res.headersSent) {
        res.writeHead(502, { "Content-Type": "application/json" });
      }
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
