import test from "node:test";
import assert from "node:assert/strict";
import worker, {
  checkAndDispatch,
  needsRefresh,
  repositoryToken,
} from "./index.mjs";
import { generateKeyPairSync, createPublicKey, verify } from "node:crypto";

const healthy = () =>
  ["carbon", "regional", "mix", "elexon", "demand", "factors"].map((id) => ({
    id,
    collection_status: "current",
    last_success_at: "2026-10-15T11:00:00Z",
  }));
const env = { GITHUB_ACTIONS_TOKEN: "test-only" };

test("complete healthy status skips workflow calls with a supplied token", async () => {
  let count = 0;
  assert.deepEqual(
    await checkAndDispatch(env, async () => {
      count++;
      return Response.json({ rows: healthy() });
    }),
    { action: "healthy" },
  );
  assert.equal(count, 1);
});

test("healthy collections still validate GitHub App authentication", async () => {
  const { privateKey } = generateKeyPairSync("rsa", { modulusLength: 2048 });
  const appEnv = {
    GITHUB_APP_ID: "123",
    GITHUB_INSTALLATION_ID: "456",
    GITHUB_APP_PRIVATE_KEY: privateKey.export({ type: "pkcs8", format: "pem" }),
  };
  let calls = 0;
  await assert.rejects(
    checkAndDispatch(appEnv, async (url) => {
      calls++;
      if (url.endsWith("/operations/sources")) return Response.json({ rows: healthy() });
      assert.equal(url, "https://api.github.com/app/installations/456/access_tokens");
      return new Response(null, { status: 401 });
    }),
    /Installation authentication failed \(401\)/,
  );
  assert.equal(calls, 2);
});
test("missing or overdue sources need recovery; upstream delay alone does not", () => {
  assert.ok(needsRefresh(healthy().slice(1)));
  const rows = healthy();
  rows[0].collection_status = "overdue";
  assert.ok(needsRefresh(rows));
  rows[0].collection_status = "source_delayed";
  assert.equal(needsRefresh(rows), false);
});
test("recovery targets only the configured workflow with due-only mode", async () => {
  let step = 0;
  const result = await checkAndDispatch(env, async (url, options) => {
    step++;
    if (step === 1) return Response.json({ rows: [] });
    if (step === 2) return Response.json({ workflow_runs: [] });
    assert.equal(
      url,
      "https://api.github.com/repos/victornonso/gridsignal-gb/actions/workflows/ingestion.yml/dispatches",
    );
    assert.deepEqual(JSON.parse(options.body), {
      ref: "main",
      inputs: { mode: "due" },
    });
    return new Response(null, { status: 204 });
  });
  assert.deepEqual(result, { action: "dispatched" });
});
test("an active refresh prevents duplicate dispatch", async () => {
  let step = 0;
  assert.deepEqual(
    await checkAndDispatch(env, async () =>
      ++step === 1
        ? Response.json({ rows: [] })
        : Response.json({ workflow_runs: [{ status: "in_progress" }] }),
    ),
    { action: "already_running" },
  );
  assert.equal(step, 2);
});
test("upstream inspection or authentication errors are visible failures", async () => {
  await assert.rejects(
    checkAndDispatch({}, async () => {}),
    /token is not configured/,
  );
  let step = 0;
  await assert.rejects(
    checkAndDispatch(env, async () =>
      ++step === 1
        ? new Response(null, { status: 503 })
        : new Response(null, { status: 401 }),
    ),
    /inspection failed \(401\)/,
  );
});
test("no public HTTP refresh endpoint is exposed", async () => {
  assert.equal(worker.fetch().status, 404);
});

test("App authentication mints short-lived tokens restricted to this repository", async () => {
  const { privateKey } = generateKeyPairSync("rsa", { modulusLength: 2048 });
  const result = await repositoryToken(
    {
      GITHUB_APP_ID: "123",
      GITHUB_INSTALLATION_ID: "456",
      GITHUB_APP_PRIVATE_KEY: privateKey.export({
        type: "pkcs1",
        format: "pem",
      }),
    },
    async (url, options) => {
      assert.equal(
        url,
        "https://api.github.com/app/installations/456/access_tokens",
      );
      assert.deepEqual(JSON.parse(options.body), {
        repositories: ["gridsignal-gb"],
        permissions: { actions: "write" },
      });
      const jwt = options.headers.Authorization.slice(7);
      const parts = jwt.split(".");
      const claims = JSON.parse(Buffer.from(parts[1], "base64url"));
      assert.equal(claims.iss, "123");
      assert.ok(claims.exp - claims.iat <= 600);
      assert.ok(
        verify(
          "RSA-SHA256",
          Buffer.from(parts.slice(0, 2).join(".")),
          createPublicKey(privateKey),
          Buffer.from(parts[2], "base64url"),
        ),
      );
      return Response.json({ token: "installation-fixture" });
    },
  );
  assert.equal(result, "installation-fixture");
});
