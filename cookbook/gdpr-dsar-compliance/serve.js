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
import { AiSdk } from "./ai-sdk.js";

const HOST = (process.env.AI_SDK_HOST || "http://localhost:8585").replace(/\/$/, "");
const TOKEN =
  process.env.AI_SDK_TOKEN ||
  "eyJraWQiOiJHYjM4OWEtOWY3Ni1nZGpzLWE5MmotMDI0MmJrOTQzNTYiLCJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJhZG1pbiIsImlzQm90IjpmYWxzZSwiaXNzIjoib3Blbi1tZXRhZGF0YS5vcmciLCJpYXQiOjE2NjM5Mzg0NjIsImVtYWlsIjoiYWRtaW5Ab3Blbm1ldGFkYXRhLm9yZyJ9.tS8um_5DKu7HgzGBzS1VTA5uUjKWOCU0B_j08WXBiEC0mr0zNREkqVfwFDD-d24HlNEbrqioLsBuFRiwIWKc1m_ZlVQbG7P36RUxhuv2vbSp80FKyNM-Tj93FDzq91jsyNmsQhyNv_fNr3TXfzzSPjHt8Go0FMMP66weoKMgW2PbXlhVKwEuXUHyakLLzewm9UMeQaEiRzhiTMU3UkLXcKbYEJJvfNFcLwSl9W8JCO_l0Yj3ud-qt_nQYEZwqW6u5nfdQllN133iikV4fM5QZsMCnm8Rq1mvLR0y9bmJiD7fwM1tmJ791TUWqmKaTnP49U493VanKpUAfzIiOiIbhg";
const AGENT_NAME = process.env.AI_SDK_AGENT || "GDPRComplianceAnalyzer";
const PORT = parseInt(process.env.PORT || "8080", 10);
const DIR = fileURLToPath(new URL(".", import.meta.url));
const MIME = { ".html": "text/html", ".js": "text/javascript" };

// ── SDK client (same pattern as the Rust TUI) ──────────────────────
const client = new AiSdk({ host: HOST, token: TOKEN });
const agent = client.agent(AGENT_NAME);

// A real report is at least this long; anything shorter is the agent
// narrating intermediate steps ("Let me get details on…").
const MIN_REPORT_LEN = 500;
const MAX_TURNS = 4;
const NUDGE =
  "Stop searching. Compile ALL findings into the full GDPR compliance " +
  "report now — affected tables, PII columns, retention conflicts, " +
  "deletion order, and risk flags. Output markdown.";
const CONTINUE =
  "Your previous response was cut off. Continue writing the report " +
  "exactly where you left off. Do not repeat any content already produced.";

/** True when the text ends mid-sentence / mid-word. */
function looksIncomplete(text) {
  const t = text.trim();
  if (!t) return true;
  return !/[.!?:)\]}\n]\s*$/.test(t);
}

createServer(async (req, res) => {
  // ── POST /api/analyze — stream SSE events to the browser ──────────
  if (req.method === "POST" && req.url === "/api/analyze") {
    try {
      const chunks = [];
      for await (const chunk of req) chunks.push(chunk);
      const { message } = JSON.parse(Buffer.concat(chunks).toString());

      // Defer SSE headers until the first event arrives — if the SDK
      // throws before producing any events we can still return a proper
      // JSON error with a non-200 status.
      let sseStarted = false;
      function ensureSSE() {
        if (!sseStarted) {
          res.writeHead(200, {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
          });
          sseStarted = true;
        }
      }

      const send = (obj) => { ensureSSE(); res.write(`data: ${JSON.stringify(obj)}\n\n`); };
      const allTools = [];

      /** Stream one turn, forwarding every event to the browser. */
      async function streamTurn(msg, convId) {
        let text = "";
        for await (const ev of agent.stream(msg, { conversationId: convId })) {
          switch (ev.type) {
            case "content":
              if (ev.content) {
                text += ev.content;
                send({ type: "content", text: ev.content });
              }
              break;
            case "tool_use":
              if (ev.toolName) allTools.push(ev.toolName);
              send({ type: "tool" });
              text = ""; // content after last tool = the report
              break;
            case "error":
              send({ type: "error", message: ev.error || "Agent error" });
              return { text: "", conversationId: convId };
          }
          if (ev.conversationId) convId = ev.conversationId;
        }
        return { text, conversationId: convId };
      }

      // First turn — the user's actual DSAR request.
      let result = await streamTurn(message, undefined);
      let reportText = result.text;

      // If the agent stopped early with a narration line, nudge it to
      // compile the actual report.
      let turn = 0;
      while (reportText.length < MIN_REPORT_LEN && turn < MAX_TURNS && result.conversationId) {
        turn++;
        console.log(`  turn ${turn}: ${reportText.length} chars — nudging agent to produce report`);
        send({ type: "turn", number: turn });
        result = await streamTurn(NUDGE, result.conversationId);
        if (result.text.length > reportText.length) reportText = result.text;
      }

      // If the report was cut off mid-sentence (LLM output-token limit),
      // ask the agent to continue from where it left off.
      while (looksIncomplete(reportText) && turn < MAX_TURNS && result.conversationId) {
        turn++;
        console.log(`  turn ${turn}: report looks truncated — asking agent to continue`);
        send({ type: "turn", number: turn });
        result = await streamTurn(CONTINUE, result.conversationId);
        if (result.text.trim()) reportText += "\n" + result.text;
      }

      send({ type: "done", report: reportText });
      res.end();
    } catch (err) {
      if (!sseStarted) {
        // SDK failed before any events — return a normal JSON error.
        res.writeHead(502, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ error: err.message }));
      } else {
        try {
          res.write(`data: ${JSON.stringify({ type: "error", message: err.message })}\n\n`);
        } catch (_) { /* stream already closed */ }
        res.end();
      }
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
