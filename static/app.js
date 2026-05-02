// Minimal client logic: two forms, fetch + FormData, error messages
// rendered inline. No frameworks, no build step.

(function () {
  "use strict";

  // ----- Backend URL --------------------------------------------------
  // On localhost (Flask serving both halves) we use same-origin paths.
  // In production (Vercel + Render) we hit the Render backend directly.
  // EDIT the production URL after deploying the backend to Render:
  const PROD_BACKEND = "https://YOUR-BACKEND.onrender.com";

  const API_BASE_URL =
    location.hostname === "localhost" || location.hostname === "127.0.0.1"
      ? ""
      : PROD_BACKEND;

  // -------------------------------------------------------------------

  const encodeForm = document.getElementById("encode-form");
  const decodeForm = document.getElementById("decode-form");
  const encodeStatus = document.getElementById("encode-status");
  const decodeStatus = document.getElementById("decode-status");
  const decodeOutput = document.getElementById("decode-output");

  // ---- helpers ---------------------------------------------------------

  function setStatus(el, kind, text) {
    el.className = "status" + (kind ? " " + kind : "");
    el.textContent = text || "";
  }

  function setBusy(form, isBusy, busyLabel) {
    const btn = form.querySelector('button[type="submit"]');
    btn.disabled = isBusy;
    if (isBusy) {
      btn.dataset.original = btn.textContent;
      btn.textContent = busyLabel;
    } else if (btn.dataset.original) {
      btn.textContent = btn.dataset.original;
      delete btn.dataset.original;
    }
  }

  async function readError(response) {
    try {
      const data = await response.json();
      if (data && data.error) return data.error;
    } catch (_) { /* not JSON */ }
    return "Request failed (HTTP " + response.status + ").";
  }

  // ---- image preview ---------------------------------------------------

  // Wires up every <span class="filebox"> with a live image preview and
  // a "filename selected" visual state.
  function wirePreviews() {
    document.querySelectorAll("[data-filebox]").forEach(function (filebox) {
      const input = filebox.querySelector('input[type="file"]');
      const text = filebox.querySelector(".filebox-text");
      const preview = filebox.parentElement.querySelector(".preview");
      const originalText = text ? text.innerHTML : "";

      input.addEventListener("change", function () {
        const file = input.files && input.files[0];
        if (!file) {
          if (preview) { preview.hidden = true; preview.removeAttribute("src"); }
          filebox.classList.remove("has-file");
          if (text) text.innerHTML = originalText;
          return;
        }

        filebox.classList.add("has-file");
        if (text) {
          text.innerHTML =
            '<strong>' + escapeHtml(file.name) + '</strong>' +
            '<br /><small>' + formatBytes(file.size) + ' · click to change</small>';
        }

        if (preview) {
          const reader = new FileReader();
          reader.onload = function (e) {
            preview.src = e.target.result;
            preview.hidden = false;
          };
          reader.readAsDataURL(file);
        }
      });
    });
  }

  function escapeHtml(s) {
    return s.replace(/[&<>"']/g, function (c) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c];
    });
  }

  function formatBytes(n) {
    if (n < 1024) return n + " B";
    if (n < 1024 * 1024) return (n / 1024).toFixed(1) + " KB";
    return (n / (1024 * 1024)).toFixed(2) + " MB";
  }

  // ---- /encode --------------------------------------------------------

  encodeForm.addEventListener("submit", async function (event) {
    event.preventDefault();
    setStatus(encodeStatus, "", "");
    setBusy(encodeForm, true, "Encrypting...");

    try {
      const response = await fetch(API_BASE_URL + "/encode", {
        method: "POST",
        body: new FormData(encodeForm),
      });

      if (!response.ok) {
        setStatus(encodeStatus, "error", await readError(response));
        return;
      }

      // --- auto-download stego.png ---------------------------------
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "stego.png";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);

      setStatus(encodeStatus, "ok", "✓ Done — stego.png downloaded.");
    } catch (err) {
      setStatus(encodeStatus, "error", "Network error: " + err.message);
    } finally {
      setBusy(encodeForm, false);
    }
  });

  // ---- /decode --------------------------------------------------------

  decodeForm.addEventListener("submit", async function (event) {
    event.preventDefault();
    setStatus(decodeStatus, "", "");
    decodeOutput.textContent = "";
    setBusy(decodeForm, true, "Decrypting...");

    try {
      const response = await fetch(API_BASE_URL + "/decode", {
        method: "POST",
        body: new FormData(decodeForm),
      });

      if (!response.ok) {
        setStatus(decodeStatus, "error", await readError(response));
        return;
      }

      const data = await response.json();
      decodeOutput.textContent = data.message || "";
      setStatus(decodeStatus, "ok", "✓ Message recovered.");
    } catch (err) {
      setStatus(decodeStatus, "error", "Network error: " + err.message);
    } finally {
      setBusy(decodeForm, false);
    }
  });

  // ---- init ------------------------------------------------------------
  wirePreviews();
})();
