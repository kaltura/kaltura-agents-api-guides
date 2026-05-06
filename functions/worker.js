export default {
  async fetch(request, env) {
    const accept = request.headers.get("Accept") || "";
    const url = new URL(request.url);

    if (
      accept.includes("text/markdown") &&
      !url.pathname.match(/\.(js|css|png|jpg|svg|ico|woff2?|xml|json)$/)
    ) {
      let name = url.pathname.replace(/^\//, "").replace(/\/$/, "");
      if (!name) name = "README";

      const mdUrl = new URL(`/raw/${name}.md`, request.url);
      const mdResponse = await env.ASSETS.fetch(mdUrl);

      if (mdResponse.ok) {
        const body = await mdResponse.text();
        return new Response(body, {
          headers: {
            "Content-Type": "text/markdown; charset=utf-8",
            Vary: "Accept",
            "X-Markdown-Tokens": String(Math.ceil(body.length / 4)),
          },
        });
      }
    }

    return env.ASSETS.fetch(request);
  },
};
