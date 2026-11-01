// Last Commit — graveyard front end. No framework, no build step.
// Routes: #/            -> graveyard
//         #/<slug>      -> one repo's ofrenda

const app = document.getElementById("app");
const cache = new Map();

const fmtYear = (iso) => (iso ? iso.slice(0, 4) : "?");
const fmtDate = (iso) =>
  iso ? new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" }) : "unknown";
const num = (n) => (n ?? 0).toLocaleString();

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null) continue;
    if (k === "class") node.className = v;
    else if (k === "text") node.textContent = v;
    else node.setAttribute(k, v);
  }
  for (const c of children.flat(Infinity)) {
    if (c == null) continue;
    node.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return node;
}

async function load(path) {
  if (!cache.has(path)) {
    cache.set(path, fetch(path).then((r) => {
      if (!r.ok) throw new Error(`${path}: ${r.status}`);
      return r.json();
    }));
  }
  return cache.get(path);
}

async function renderGraveyard() {
  document.title = "Last Commit — a graveyard for dead repos";
  const graves = await load("data/index.json");
  if (!graves.length) {
    app.replaceChildren(el("p", { class: "empty", text: "The graveyard is empty. Hold a séance first." }));
    return;
  }
  const tpl = document.getElementById("tomb-tpl");
  const grid = el("section", { class: "graveyard", "aria-label": "Graves" });
  for (const g of graves) {
    const tomb = tpl.content.firstElementChild.cloneNode(true);
    tomb.href = `#/${encodeURIComponent(g.slug)}`;
    tomb.querySelector(".tomb-name").textContent = g.name;
    tomb.querySelector(".tomb-dates").textContent = `${fmtYear(g.born)} – ${fmtYear(g.died)}`;
    tomb.querySelector(".tomb-epitaph").textContent = g.epitaph || "";
    tomb.setAttribute("aria-label", `${g.name}, ${fmtYear(g.born)} to ${fmtYear(g.died)}`);
    grid.append(tomb);
  }
  app.replaceChildren(grid);
}

function factsPanel(f) {
  const rows = [
    ["Repository", el("a", { href: f.url, text: f.full_name })],
    ["Was", (f.description || "").replace(/:[a-z0-9_+-]+:/g, "").trim() || "—"],
    ["Language", f.language || "—"],
    ["First commit", f.first_commit
      ? el("span", {}, fmtDate(f.born), " · ", el("a", { href: f.first_commit.url, text: `“${f.first_commit.message}”` }))
      : fmtDate(f.born)],
    ["Last commit", f.last_commit
      ? el("span", {}, fmtDate(f.died), " · ", el("a", { href: f.last_commit.url, text: `“${f.last_commit.message}”` }))
      : fmtDate(f.died)],
    ["Lifespan", `${f.lifespan_years} years`],
    ["Silent for", `${f.years_since_last_commit} years`],
    ["Commits", num(f.total_commits)],
    ["Stars · forks", `${num(f.stars)} · ${num(f.forks)}`],
    ["Left open", `${num(f.open_issues)} issues and PRs`],
    ["Status", f.archived ? "Archived (read-only)" : "Never archived"],
  ];
  if (f.latest_release) rows.push(["Last release", `${f.latest_release.tag} · ${fmtDate(f.latest_release.date)}`]);
  if (f.top_contributors?.length) {
    const n = f.top_contributors.length;
    const total = f.top_contributors.reduce((s, c) => s + c.contributions, 0);
    rows.push(["Mourned by", `Top ${n} contributor${n > 1 ? "s" : ""}, ${num(total)} commits between them`]);
  }

  return el("section", { class: "panel facts" },
    el("h3", { text: "What is true" }),
    el("span", { class: "label", text: "Verified facts" }),
    el("dl", {}, rows.map(([k, v]) => [el("dt", { text: k }), el("dd", {}, v)])),
    el("p", { class: "source", text: `From the GitHub API, fetched ${fmtDate(f.fetched_at)}.` }),
  );
}

function ghostPanel(record) {
  const g = record.ghost;
  if (!g) {
    return el("section", { class: "panel ghost" },
      el("h3", { text: "The ghost speaks" }),
      el("p", { class: "credit", text: "This spirit has not been summoned yet." }));
  }
  return el("section", { class: "panel ghost" },
    el("h3", { text: "The ghost speaks" }),
    el("span", { class: "label", text: "Fiction" }),
    record.audio ? el("audio", { controls: "", preload: "none", src: record.audio }) : null,
    el("div", { class: "monologue" }, g.monologue.split(/\n\n+/).map((p) => el("p", { text: p }))),
    el("p", { class: "credit", text:
      `Imagined by ${g.model} (${g.provider === "ollama" ? "running locally" : "via Google AI Studio"})` +
      (record.audio ? ", voiced by ElevenLabs." : ".") +
      " It speaks as the code, never for the people who wrote it." }),
  );
}

async function renderOfrenda(slug) {
  const record = await load(`data/${slug}.json`);
  const f = record.facts;
  document.title = `${f.full_name} — Last Commit`;
  app.replaceChildren(
    el("a", { class: "back", href: "#/", text: "← Back to the graveyard" }),
    el("header", { class: "ofrenda-head" },
      el("h2", { text: f.full_name }),
      el("div", { class: "dates", text: `${fmtYear(f.born)} – ${fmtYear(f.died)}` }),
      record.ghost?.epitaph ? el("p", { class: "epitaph", text: `“${record.ghost.epitaph}”` }) : null,
    ),
    el("div", { class: "ofrenda" }, factsPanel(f), ghostPanel(record)),
  );
  window.scrollTo(0, 0);
}

async function route() {
  const slug = decodeURIComponent(location.hash.replace(/^#\/?/, ""));
  try {
    if (slug && /^[\w.-]+__[\w.-]+$/.test(slug)) await renderOfrenda(slug);
    else await renderGraveyard();
  } catch (err) {
    console.error(err);
    app.replaceChildren(el("p", { class: "empty", text: "That grave could not be found." }),
      el("p", { class: "empty" }, el("a", { href: "#/", text: "Back to the graveyard" })));
  }
}

window.addEventListener("hashchange", route);
route();
