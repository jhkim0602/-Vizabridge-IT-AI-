import { NextResponse } from "next/server";
import { promises as fs } from "fs";
import path from "path";

export const dynamic = "force-dynamic";

const STORE_PATH = path.join(process.cwd(), "data", "submissions.json");
const ADMIN_TOKEN = "1234";

async function readStore(): Promise<unknown[]> {
  try {
    const raw = await fs.readFile(STORE_PATH, "utf8");
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch (e: unknown) {
    if ((e as NodeJS.ErrnoException).code === "ENOENT") return [];
    throw e;
  }
}

async function writeStore(items: unknown[]): Promise<void> {
  await fs.mkdir(path.dirname(STORE_PATH), { recursive: true });
  await fs.writeFile(STORE_PATH, JSON.stringify(items, null, 2), "utf8");
}

export async function POST(req: Request) {
  const body = await req.json().catch(() => null);
  if (!body || typeof body !== "object") {
    return NextResponse.json({ error: "invalid body" }, { status: 400 });
  }
  const items = await readStore();
  const record = {
    receivedAt: new Date().toISOString(),
    ...(body as Record<string, unknown>),
  };
  items.push(record);
  await writeStore(items);
  return NextResponse.json({ ok: true, count: items.length });
}

export async function GET(req: Request) {
  const auth =
    req.headers.get("x-admin-token") ??
    new URL(req.url).searchParams.get("token");
  if (auth !== ADMIN_TOKEN) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }
  const items = await readStore();
  return NextResponse.json({ items });
}
