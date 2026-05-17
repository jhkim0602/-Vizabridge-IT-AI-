import { NextResponse } from "next/server";
import { kv } from "@vercel/kv";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const LIST_KEY = "vizabridge:submissions";
const ADMIN_TOKEN = "1234";

function kvAvailable() {
  return Boolean(process.env.KV_REST_API_URL && process.env.KV_REST_API_TOKEN);
}

export async function POST(req: Request) {
  if (!kvAvailable()) {
    return NextResponse.json(
      { error: "storage not configured" },
      { status: 503 },
    );
  }
  const body = await req.json().catch(() => null);
  if (!body || typeof body !== "object") {
    return NextResponse.json({ error: "invalid body" }, { status: 400 });
  }
  const record = {
    receivedAt: new Date().toISOString(),
    ...(body as Record<string, unknown>),
  };
  await kv.lpush(LIST_KEY, JSON.stringify(record));
  return NextResponse.json({ ok: true });
}

export async function GET(req: Request) {
  const auth =
    req.headers.get("x-admin-token") ??
    new URL(req.url).searchParams.get("token");
  if (auth !== ADMIN_TOKEN) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }
  if (!kvAvailable()) {
    return NextResponse.json({ items: [], storageConfigured: false });
  }
  const raw = await kv.lrange<string | Record<string, unknown>>(
    LIST_KEY,
    0,
    -1,
  );
  const items = raw.map((entry) =>
    typeof entry === "string" ? JSON.parse(entry) : entry,
  );
  return NextResponse.json({ items, storageConfigured: true });
}
