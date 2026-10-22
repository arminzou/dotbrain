// Pi entry point for the dotbrain extension.
//
// Hands Pi the packaged skills beside this file. Pi honors each skill's own
// `disable-model-invocation` frontmatter, so explicit-only skills stay manual: hidden from the
// model, still available as `/skill:<name>`. Pi ranks these below the user's own skills, so a
// same-named skill of the user's wins and none loads twice.
//
// Session hooks hand each Pi event to `dotbrain hook run`, which decides wiring, assembles the
// convention and syncs; this file only maps events and caches what the CLI printed:
//
// - `session_start` runs the CLI once per session (startup, resume, `new` as clear, reload and
//   fork as compaction: push only, never a second full sync) and caches the convention;
// - `before_agent_start` adds the cached convention as a system prompt section on every run,
//   since Pi drops a section a run omits; compaction needs no call, the section survives it;
// - `agent_settled` ends each run: `turn-end` pushes in the background;
// - `session_shutdown` for `quit` runs `session-end`, which schedules a full sync; other reasons
//   replace the session, and the next `session_start` covers them.
//
// Every hook fails open: a missing, slow or failing `dotbrain` leaves the agent untouched.
//
// Pi runs this in its own process: Node built-ins only.

import { spawn } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

export const VERSION = "0.12.0"; // x-release-please-version

const SKILLS = join(dirname(fileURLToPath(import.meta.url)), "skills");

// Pi time-boxes no handler; the CLI's session start waits at most 10 s for sync.
const START_TIMEOUT_MS = 15_000;
// session-end only launches a detached sync and returns.
const END_TIMEOUT_MS = 5_000;
const START_EVENTS = { startup: "startup", resume: "resume", new: "clear", reload: "compaction", fork: "compaction" };

const argv = (event, checkout) => ["hook", "run", "--event", event, "--checkout", checkout];

// What `dotbrain hook run` printed for this event; "" when it is missing, fails or overruns.
function run(event, checkout, timeoutMs) {
  return new Promise((resolve) => {
    let out = "";
    let child;
    const timer = setTimeout(() => {
      child?.kill();
      resolve("");
    }, timeoutMs);
    const done = (text) => {
      clearTimeout(timer);
      resolve(text);
    };
    try {
      child = spawn("dotbrain", argv(event, checkout), { stdio: ["ignore", "pipe", "ignore"], windowsHide: true });
      child.stdout.setEncoding("utf8");
      child.stdout.on("data", (chunk) => { out += chunk; });
      child.on("error", () => done(""));
      child.on("close", (code) => done(code === 0 ? out.trim() : ""));
    } catch {
      done("");
    }
  });
}

// Detached so the push outlives Pi: on Windows a non-detached child dies with Pi's job object.
function launch(event, checkout) {
  const child = spawn("dotbrain", argv(event, checkout), { detached: true, stdio: "ignore", windowsHide: true });
  child.on("error", () => {});
  child.unref();
}

// A hook must never break the agent.
const failOpen = (handler) => async (event, ctx) => {
  try {
    await handler(event, ctx);
  } catch {
    // fail open
  }
};

export default function (pi) {
  let convention = ""; // what the CLI printed for this session; "" when unwired

  pi.on("resources_discover", () => ({ skillPaths: [SKILLS] }));
  pi.on("session_start", failOpen(async (event, ctx) => {
    // An unknown reason still gets the convention, without a full sync.
    convention = await run(START_EVENTS[event.reason] ?? "compaction", ctx.cwd, START_TIMEOUT_MS);
  }));
  pi.on("before_agent_start", failOpen((event) => {
    if (convention) event.systemPromptOptions.sections.dotbrain = convention;
  }));
  // Closing the Windows console likely skips session_shutdown, so this push is the durability point.
  pi.on("agent_settled", failOpen((event, ctx) => launch("turn-end", ctx.cwd)));
  pi.on("session_shutdown", failOpen(async (event, ctx) => {
    if (event.reason === "quit") await run("session-end", ctx.cwd, END_TIMEOUT_MS);
  }));
}
