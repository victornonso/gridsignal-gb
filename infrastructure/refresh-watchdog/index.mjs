const REPOSITORY = "https://api.github.com/repos/victornonso/gridsignal-gb";
const WORKFLOW = `${REPOSITORY}/actions/workflows/ingestion.yml`;
const STATUS = "https://gridsignal-api.onrender.com/api/v1/operations/sources";
const SOURCES = ["carbon", "regional", "mix", "elexon", "demand", "factors"];

function base64url(bytes) {
  return btoa(String.fromCharCode(...bytes))
    .replaceAll("+", "-")
    .replaceAll("/", "_")
    .replace(/=+$/, "");
}

function derLength(value) {
  if (value < 128) return [value];
  const bytes = [];
  while (value > 0) {
    bytes.unshift(value & 255);
    value >>>= 8;
  }
  return [0x80 | bytes.length, ...bytes];
}

export async function repositoryToken(env, request) {
  if (env.GITHUB_ACTIONS_TOKEN) return env.GITHUB_ACTIONS_TOKEN;
  const pem = env.GITHUB_APP_PRIVATE_KEY.replaceAll("\\n", "\n");
  const raw = Uint8Array.from(
    atob(pem.replace(/-----[^-]+-----|\s/g, "")),
    (c) => c.charCodeAt(0),
  );
  const wrapped = pem.includes("BEGIN RSA PRIVATE KEY")
    ? (() => {
        const algorithm = [
          2, 1, 0, 48, 13, 6, 9, 42, 134, 72, 134, 247, 13, 1, 1, 1, 5, 0,
        ];
        const contents = [...algorithm, 4, ...derLength(raw.length), ...raw];
        return new Uint8Array([48, ...derLength(contents.length), ...contents]);
      })()
    : raw;
  const key = await crypto.subtle.importKey(
    "pkcs8",
    wrapped,
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const now = Math.floor(Date.now() / 1000);
  const encode = (value) =>
    base64url(new TextEncoder().encode(JSON.stringify(value)));
  const body = `${encode({ alg: "RS256", typ: "JWT" })}.${encode({ iat: now - 30, exp: now + 540, iss: env.GITHUB_APP_ID })}`;
  const signature = await crypto.subtle.sign(
    "RSASSA-PKCS1-v1_5",
    key,
    new TextEncoder().encode(body),
  );
  const response = await request(
    `https://api.github.com/app/installations/${env.GITHUB_INSTALLATION_ID}/access_tokens`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${body}.${base64url(new Uint8Array(signature))}`,
        Accept: "application/vnd.github+json",
        "User-Agent": "GridSignal-refresh-watchdog",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        repositories: ["gridsignal-gb"],
        permissions: { actions: "write" },
      }),
      signal: AbortSignal.timeout(20000),
    },
  );
  if (!response.ok)
    throw new Error(`Installation authentication failed (${response.status}).`);
  const token = (await response.json()).token;
  if (!token) throw new Error("Installation token was not returned.");
  return token;
}

export function needsRefresh(rows) {
  if (!Array.isArray(rows)) return true;
  return SOURCES.some((id) => {
    const source = rows.find((row) => row.id === id);
    return (
      !source ||
      !source.last_success_at ||
      ["overdue", "failed", "no_data"].includes(source.collection_status)
    );
  });
}

export async function checkAndDispatch(env, request = fetch) {
  if (
    !env.GITHUB_ACTIONS_TOKEN &&
    !(
      env.GITHUB_APP_ID &&
      env.GITHUB_INSTALLATION_ID &&
      env.GITHUB_APP_PRIVATE_KEY
    )
  )
    throw new Error("Repository-scoped Actions token is not configured.");
  let required = true;
  try {
    const response = await request(STATUS, {
      signal: AbortSignal.timeout(95000),
    });
    if (response.ok) required = needsRefresh((await response.json()).rows);
  } catch {
    // A cold or unavailable API must not disable the independent recovery trigger.
  }
  // Validate machine authentication on every check so revoked access is visible early.
  const token = await repositoryToken(env, request);
  if (!required) return { action: "healthy" };
  const headers = {
    Authorization: `Bearer ${token}`,
    Accept: "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "GridSignal-refresh-watchdog",
  };
  const runs = await request(`${WORKFLOW}/runs?per_page=5`, {
    headers,
    signal: AbortSignal.timeout(20000),
  });
  if (!runs.ok) throw new Error(`Workflow inspection failed (${runs.status}).`);
  const active = (await runs.json()).workflow_runs.some((run) =>
    ["queued", "in_progress", "waiting", "pending", "requested"].includes(
      run.status,
    ),
  );
  if (active) return { action: "already_running" };
  const dispatched = await request(`${WORKFLOW}/dispatches`, {
    method: "POST",
    headers: { ...headers, "Content-Type": "application/json" },
    body: JSON.stringify({ ref: "main", inputs: { mode: "due" } }),
    signal: AbortSignal.timeout(20000),
  });
  if (dispatched.status !== 204)
    throw new Error(`Refresh dispatch failed (${dispatched.status}).`);
  return { action: "dispatched" };
}

export default {
  async scheduled(_event, env) {
    console.log(JSON.stringify(await checkAndDispatch(env)));
  },
  fetch() {
    return new Response("Not found", { status: 404 });
  },
};
