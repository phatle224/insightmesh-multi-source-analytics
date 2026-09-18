export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const response = await fetch(
      `${process.env.BACKEND_INTERNAL_URL ?? "http://backend:8000"}/api/v1/health`,
      { cache: "no-store", signal: AbortSignal.timeout(3000) },
    );
    if (!response.ok) throw new Error("Backend unavailable");
    return Response.json({ status: "ok", service: "frontend", backend: "ok" });
  } catch {
    return Response.json({ status: "unavailable" }, { status: 503 });
  }
}
