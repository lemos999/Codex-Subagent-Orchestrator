const fs = require("fs");
const path = require("path");

const args = process.argv.slice(2);
const joinedArgs = args.join(" ");
const useJson = joinedArgs.includes("--json");
const mode = process.env.MOCK_CODEX_MODE || "success";

let lastMessagePath = null;
for (let i = 0; i < args.length; i += 1) {
  if ((args[i] === "-o" || args[i] === "--output-last-message") && i + 1 < args.length) {
    lastMessagePath = args[i + 1];
    break;
  }
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function writeLine(line) {
  process.stdout.write(`${line}\n`);
}

async function main() {
  if (useJson) {
    writeLine(JSON.stringify({
      type: "thread.started",
      thread_id: "mock-thread"
    }));
    await sleep(250);

    writeLine(JSON.stringify({
      type: "turn.started",
      turn_id: "mock-turn"
    }));
    await sleep(250);

    if (mode === "fail") {
      writeLine(JSON.stringify({
        type: "error",
        message: "stream disconnected before completion: error sending request for url (https://api.openai.com/v1/responses)"
      }));
      await sleep(250);

      writeLine(JSON.stringify({
        type: "turn.failed",
        error: {
          message: "stream disconnected before completion: error sending request for url (https://api.openai.com/v1/responses)"
        }
      }));
      await sleep(250);

      writeLine(JSON.stringify({
        type: "error",
        message: "Failed to shutdown rollout recorder"
      }));
      return;
    }

    writeLine(JSON.stringify({
      method: "thread/tokenUsage/updated",
      params: {
        threadId: "mock-thread",
        turnId: "mock-turn",
        tokenUsage: {
          last: {
            cachedInputTokens: 0,
            inputTokens: 50,
            outputTokens: 10,
            reasoningOutputTokens: 5,
            totalTokens: 65
          },
          total: {
            cachedInputTokens: 0,
            inputTokens: 50,
            outputTokens: 10,
            reasoningOutputTokens: 5,
            totalTokens: 65
          },
          modelContextWindow: 200000
        }
      }
    }));
    await sleep(1400);

    writeLine(JSON.stringify({
      type: "event_msg",
      payload: {
        type: "token_count",
        info: {
          total_token_usage: {
            cached_input_tokens: 0,
            input_tokens: 200,
            output_tokens: 80,
            reasoning_output_tokens: 41,
            total_tokens: 321
          }
        }
      }
    }));
    await sleep(250);
  } else {
    writeLine("tokens used");
    writeLine("321");
    await sleep(500);
  }

  if (lastMessagePath && mode !== "fail") {
    fs.mkdirSync(path.dirname(lastMessagePath), { recursive: true });
    fs.writeFileSync(lastMessagePath, "Mock worker completed.\n", "utf8");
  }
}

main().catch((error) => {
  process.stderr.write(`${error && error.stack ? error.stack : String(error)}\n`);
  process.exitCode = 1;
});
