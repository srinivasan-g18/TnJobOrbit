document.addEventListener("DOMContentLoaded", () => {
  const menu = document.querySelector(".menu-btn");
  const nav = document.querySelector(".nav-links");
  if (menu && nav) menu.addEventListener("click", () => nav.classList.toggle("open"));

  document.querySelectorAll("[data-bookmark]").forEach(btn => {
    const id = btn.dataset.bookmark;
    const key = "tnjoborbit_bookmarks";
    let saved = JSON.parse(localStorage.getItem(key) || "[]");
    if (saved.includes(id)) btn.textContent = "★ Saved";
    btn.addEventListener("click", () => {
      saved = JSON.parse(localStorage.getItem(key) || "[]");
      if (saved.includes(id)) {
        saved = saved.filter(x => x !== id);
        btn.textContent = "☆ Save";
      } else {
        saved.push(id);
        btn.textContent = "★ Saved";
      }
      localStorage.setItem(key, JSON.stringify(saved));
    });
  });

  document.querySelectorAll("[data-recent]").forEach(el => {
    const id = el.dataset.recent;
    const recent = JSON.parse(localStorage.getItem("tnjoborbit_recent") || "[]");
    const updated = [id, ...recent.filter(x => x !== id)].slice(0, 30);
    localStorage.setItem("tnjoborbit_recent", JSON.stringify(updated));
  });

  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/service-worker.js").catch(() => {});
  }
});
