(function () {
  const input = document.getElementById("site-search-input");
  const resultsBox = document.getElementById("site-search-results");
  const body = document.body;
  const baseurl = body ? body.getAttribute("data-baseurl") || "" : "";
  const searchIndexUrl = `${baseurl}/search.json`;
  if (!input || !resultsBox) {
    return;
  }

  let indexData = null;

  const escapeHtml = (value) =>
    String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");

  const renderResults = (items, query) => {
    if (!query || query.length < 2) {
      resultsBox.hidden = true;
      resultsBox.innerHTML = "";
      return;
    }

    if (items.length === 0) {
      resultsBox.hidden = false;
      resultsBox.innerHTML = '<p class="search-empty">검색 결과가 없습니다.</p>';
      return;
    }

    const html = items
      .slice(0, 8)
      .map(
        (item) => `
          <a class="search-item" href="${item.url}">
            <strong>${escapeHtml(item.title)}</strong>
            <small>${escapeHtml(item.date)} · ${escapeHtml(item.categories)}</small>
            <span>${escapeHtml((item.content || "").slice(0, 90))}...</span>
          </a>
        `
      )
      .join("");

    resultsBox.hidden = false;
    resultsBox.innerHTML = html;
  };

  const runSearch = (query) => {
    const q = query.trim().toLowerCase();
    if (!indexData) {
      return;
    }
    if (q.length < 2) {
      renderResults([], "");
      return;
    }

    const filtered = indexData.filter((item) => {
      const title = (item.title || "").toLowerCase();
      const content = (item.content || "").toLowerCase();
      return title.includes(q) || content.includes(q);
    });

    renderResults(filtered, q);
  };

  fetch(searchIndexUrl)
    .then((response) => response.json())
    .then((json) => {
      indexData = json;
    })
    .catch(() => {
      resultsBox.hidden = false;
      resultsBox.innerHTML = '<p class="search-empty">검색 인덱스를 불러오지 못했습니다.</p>';
    });

  input.addEventListener("input", (event) => {
    runSearch(event.target.value);
  });

  document.addEventListener("click", (event) => {
    if (!resultsBox.contains(event.target) && event.target !== input) {
      resultsBox.hidden = true;
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      resultsBox.hidden = true;
      input.blur();
    }
  });
})();
