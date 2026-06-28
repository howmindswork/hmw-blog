/* HMW unified tracking snippet. Vanilla JS, no frameworks.
   Sends pageviews + click events to the shared analytics worker and
   persists first-touch UTM attribution so it follows a visitor to checkout.
   Same script is served from blog.howmindswork.org/assets/hmw-track.js and
   from howmindswork.org/assets/hmw-track.js (apex worker). localStorage is
   per-origin, which is fine: every embedded checkout is same-origin as its
   landing page, so attribution persists landing -> checkout. */
(function () {
  "use strict";
  var ENDPOINT = "https://hmw-analytics.howmindswork.workers.dev";
  var STORE_KEY = "hmw_attr";
  var UTM_FIELDS = [
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
  ];

  function lsGet(k) {
    try {
      return window.localStorage.getItem(k);
    } catch (e) {
      return null;
    }
  }
  function lsSet(k, v) {
    try {
      window.localStorage.setItem(k, v);
    } catch (e) {}
  }

  // ── First-touch attribution ───────────────────────────
  function captureAttribution() {
    var stored = null;
    try {
      stored = JSON.parse(lsGet(STORE_KEY) || "null");
    } catch (e) {
      stored = null;
    }

    var qs = new URLSearchParams(window.location.search);
    var hasUtm = UTM_FIELDS.some(function (f) {
      return qs.get(f);
    });

    // First touch wins. Only write if nothing stored yet, OR this visit
    // carries explicit UTM params (a fresh campaign click) and the stored
    // record had none.
    if (stored && !(hasUtm && !stored.utm_source)) {
      return stored;
    }

    var refHost = "";
    try {
      refHost = document.referrer
        ? new URL(document.referrer).hostname.replace(/^www\./, "")
        : "";
    } catch (e) {
      refHost = "";
    }

    var attr = stored || {};
    UTM_FIELDS.forEach(function (f) {
      var v = qs.get(f);
      if (v) attr[f] = v.slice(0, 120);
    });
    if (!attr.utm_source && refHost) attr.utm_source = refHost;
    if (!attr.utm_source) attr.utm_source = "direct";
    attr.referrer = (document.referrer || "").slice(0, 300);
    if (!attr.landing) attr.landing = window.location.pathname.slice(0, 200);
    if (!attr.first_seen) attr.first_seen = Date.now();

    lsSet(STORE_KEY, JSON.stringify(attr));
    return attr;
  }

  var attribution = captureAttribution();

  function source() {
    return (attribution && attribution.utm_source) || "direct";
  }
  function page() {
    return window.location.pathname || "/";
  }

  // ── Pageview ──────────────────────────────────────────
  function sendPageview() {
    var u =
      ENDPOINT +
      "/track?page=" +
      encodeURIComponent(page()) +
      "&ref=" +
      encodeURIComponent(source());
    try {
      fetch(u, { method: "GET", keepalive: true, mode: "cors" }).catch(
        function () {},
      );
    } catch (e) {}
  }

  // ── Events ────────────────────────────────────────────
  function sendEvent(name, extra) {
    var payload = {
      name: name,
      page: page(),
      referrer_source: source(),
    };
    if (extra && typeof extra === "object") {
      for (var k in extra) {
        if (Object.prototype.hasOwnProperty.call(extra, k)) payload[k] = extra[k];
      }
    }
    try {
      fetch(ENDPOINT + "/event", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        keepalive: true,
        mode: "cors",
      }).catch(function () {});
    } catch (e) {}
  }

  // ── CTA / checkout click detection ────────────────────
  function isCta(el) {
    if (!el) return false;
    if (el.hasAttribute && el.hasAttribute("data-track")) return true;
    var href = (el.getAttribute && el.getAttribute("href")) || "";
    if (/checkout|buy|stripe|gumroad|order|cart|purchase/i.test(href)) return true;
    var id = (el.id || "") + " " + (el.className || "");
    if (/cta|checkout|buy|purchase|order|sticky/i.test(id)) return true;
    return false;
  }

  document.addEventListener(
    "click",
    function (e) {
      var el = e.target;
      var hops = 0;
      while (el && hops < 4) {
        if (isCta(el)) {
          var label =
            (el.getAttribute && el.getAttribute("data-track")) ||
            el.id ||
            (el.textContent || "").trim().slice(0, 40) ||
            "cta";
          sendEvent("cta_click", { label: label, cta_clicked: 1 });
          return;
        }
        el = el.parentElement;
        hops++;
      }
    },
    true,
  );

  // ── Public API ────────────────────────────────────────
  window.HMW = window.HMW || {};
  window.HMW.getAttribution = function () {
    return attribution;
  };
  window.HMW.track = function (name, extra) {
    sendEvent(name, extra);
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", sendPageview);
  } else {
    sendPageview();
  }
})();
