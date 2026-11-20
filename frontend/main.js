const connection = document.querySelector("#connection");
const version = document.querySelector("#version");
const modules = document.querySelector("#modules");

const humanize = (name) => name.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());

async function loadStatus() {
  try {
    const response = await fetch("/api/v1/system/status", { cache: "no-store" });
    if (!response.ok) throw new Error("HTTP " + response.status);
    const data = await response.json();
    connection.textContent = "API connected";
    connection.classList.add("connected");
    version.textContent = "Backend " + data.version + " · " + data.status;
    modules.replaceChildren();
    for (const [key, enabled] of Object.entries(data.capabilities)) {
      const row = document.createElement("div");
      row.className = "module";
      const label = document.createElement("span");
      label.textContent = humanize(key);
      const state = document.createElement("span");
      state.className = "module-state";
      state.textContent = enabled ? "Available" : "Planned";
      row.append(label, state);
      modules.append(row);
    }
  } catch (error) {
    connection.textContent = "API unavailable";
    connection.classList.add("error");
    version.textContent = "Unable to contact the Maratoncito backend.";
    modules.replaceChildren();
  }
}

loadStatus();
