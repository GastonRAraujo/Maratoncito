const $ = (selector) => document.querySelector(selector);
let selectedMedia = null;

function textElement(tag, content, className = "") {
  const node = document.createElement(tag);
  node.textContent = content;
  if (className) node.className = className;
  return node;
}

function showMessage(message) {
  $("#notice").textContent = message;
}

async function api(path, options = {}) {
  const response = await fetch(path, { ...options, headers: { "Content-Type": "application/json", ...options.headers } });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : `Request failed: ${response.status}`);
  return body;
}

async function loadStatus() {
  try {
    const status = await api("/api/v1/system/status");
    $("#connection").textContent = `API connected · ${status.status}`;
    $("#connection").classList.add("connected");
    const missing = Object.entries(status.capabilities).filter(([name, on]) => ["metadata", "indexers", "downloads"].includes(name) && !on).map(([name]) => name);
    if (missing.length) showMessage(`Configure required integrations in .env: ${missing.join(", ")}.`);
  } catch (error) {
    $("#connection").textContent = "API unavailable";
    showMessage(error.message);
  }
}

$("#catalog-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const list = $("#catalog");
  list.replaceChildren(textElement("p", "Searching metadata…", "secondary"));
  $("#release-section").classList.add("hidden");
  try {
    const query = new URLSearchParams({ q: $("#query").value, kind: $("#kind").value });
    const items = await api(`/api/v1/catalog/search?${query}`);
    list.replaceChildren();
    if (!items.length) list.append(textElement("p", "No matching titles found.", "secondary"));
    for (const media of items) {
      const row = document.createElement("div");
      row.className = "row";
      row.append(textElement("span", `${media.title} ${media.year ?? ""} · ${media.kind}`));
      const button = textElement("button", "Select", "secondary-button");
      button.type = "button";
      button.addEventListener("click", () => {
        selectedMedia = media;
        $("#selected-media").textContent = `${media.title} ${media.year ?? ""} · ${media.kind}`;
        $("#episode-inputs").classList.toggle("hidden", media.kind !== "series");
        $("#release-section").classList.remove("hidden");
        $("#releases").replaceChildren();
      });
      row.append(button);
      list.append(row);
    }
  } catch (error) {
    list.replaceChildren(textElement("p", error.message, "error"));
  }
});

$("#release-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!selectedMedia) return;
  const list = $("#releases");
  list.replaceChildren(textElement("p", "Searching indexers…", "secondary"));
  const body = {
    media: selectedMedia,
    profile: {
      resolutions: [$("#resolution").value],
      audio_mode: "original",
      subtitle_languages: ["es"],
    },
    episode: selectedMedia.kind === "series" ? {
      series_id: selectedMedia.id,
      season_number: Number($("#season").value),
      episode_number: Number($("#episode").value),
    } : null,
  };
  try {
    const matches = await api("/api/v1/releases/search", { method: "POST", body: JSON.stringify(body) });
    list.replaceChildren();
    if (!matches.length) list.append(textElement("p", "No releases returned by Prowlarr.", "secondary"));
    for (const { candidate, decision } of matches) {
      const card = document.createElement("article");
      card.className = "result";
      card.append(textElement("h3", candidate.title));
      const metadata = [
        candidate.indexer,
        candidate.parsed.resolution ?? "unknown resolution",
        candidate.parsed.release_group ?? "unknown group",
        candidate.seeders === null ? "unknown seeders" : `${candidate.seeders} seeders`,
        decision.score === null ? "unscored" : `score ${decision.score}`,
      ];
      card.append(textElement("p", metadata.join(" · "), "secondary"));
      card.append(textElement("p", `${decision.outcome}: ${decision.reasons.join("; ")}`, decision.outcome === "rejected" ? "error" : "secondary"));
      const button = textElement("button", decision.outcome === "rejected" ? "Rejected" : "Download selected release");
      button.type = "button";
      button.disabled = decision.outcome === "rejected";
      button.addEventListener("click", async () => {
        const review = decision.outcome === "needs_review";
        if (review && !window.confirm("Some properties are unverified. Download this exact release anyway?")) return;
        button.disabled = true;
        try {
          await api("/api/v1/downloads", {
            method: "POST",
            body: JSON.stringify({ candidate_id: candidate.id, confirm_unverified: review }),
          });
          showMessage(`Submitted: ${candidate.title}`);
          await refreshQueue();
        } catch (error) {
          showMessage(error.message);
        } finally {
          button.disabled = false;
        }
      });
      card.append(button);
      list.append(card);
    }
  } catch (error) {
    list.replaceChildren(textElement("p", error.message, "error"));
  }
});

async function refreshQueue() {
  const list = $("#queue");
  try {
    const torrents = await api("/api/v1/downloads");
    list.replaceChildren();
    if (!torrents.length) list.append(textElement("p", "No Maratoncito torrents in qBittorrent.", "secondary"));
    for (const torrent of torrents) {
      const row = document.createElement("div");
      row.className = "row";
      row.append(textElement("span", torrent.name));
      row.append(textElement("span", `${Math.round(torrent.progress * 100)}% · ${torrent.state}`, "secondary"));
      list.append(row);
    }
  } catch (error) {
    list.replaceChildren(textElement("p", error.message, "secondary"));
  }
}

$("#refresh").addEventListener("click", refreshQueue);
loadStatus();
refreshQueue();
