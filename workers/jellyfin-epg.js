const XMLTV_URL = "https://raw.githubusercontent.com/913AycltFM/91.3-Ayclt-FM-TV/main/91.3_Ayclt_FM_radio_guide.xml";

export default {
  async fetch(request) {
    if (request.method !== "GET" && request.method !== "HEAD") {
      return new Response("Method Not Allowed", { status: 405, headers: { Allow: "GET, HEAD" } });
    }

    const sourceUrl = new URL(XMLTV_URL);
    sourceUrl.searchParams.set("_epg_refresh", Date.now().toString());

    const upstream = await fetch(sourceUrl.toString(), {
      method: request.method,
      headers: {
        "User-Agent": "91.3-Ayclt-FM-Jellyfin-EPG/1.0",
        "Accept": "application/xml,text/xml,*/*",
        "Cache-Control": "no-cache",
      },
      cf: { cacheTtl: 0, cacheEverything: false },
    });

    if (!upstream.ok) {
      return new Response("Unable to retrieve the current XMLTV guide.", {
        status: 502,
        headers: { "Content-Type": "text/plain; charset=utf-8", "Cache-Control": "no-store" },
      });
    }

    const headers = new Headers(upstream.headers);
    headers.set("Content-Type", "application/xml; charset=utf-8");
    headers.set("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0");
    headers.set("Pragma", "no-cache");
    headers.set("Expires", "0");
    headers.delete("ETag");
    headers.delete("Last-Modified");
    headers.delete("Age");

    return new Response(request.method === "HEAD" ? null : upstream.body, {
      status: upstream.status,
      headers,
    });
  },
};
