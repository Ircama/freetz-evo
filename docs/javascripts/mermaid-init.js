(function () {
  "use strict";

  function renderMermaid() {
    if (typeof mermaid === "undefined") {
      return;
    }

    mermaid.initialize({
      startOnLoad: false,
      securityLevel: "loose",
      theme: "default"
    });

    // MkDocs/Material may emit Mermaid blocks in different shapes:
    // 1) <pre class="mermaid"><code>...</code></pre>
    // 2) <pre><code class="language-mermaid">...</code></pre>
    // 3) already-normalized <div class="mermaid">...</div>
    // Normalize (1) and (2) to a clean <div class="mermaid">...</div>.
    document
      .querySelectorAll("pre.mermaid, pre code.language-mermaid, pre code.mermaid")
      .forEach(function (node) {
        var pre = node.tagName === "PRE" ? node : node.parentElement;
        if (!pre || pre.dataset.mermaidRendered === "1") {
          return;
        }

        var sourceCode = "";
        if (node.tagName === "PRE") {
          var nestedCode = node.querySelector("code");
          sourceCode = nestedCode ? nestedCode.textContent : node.textContent;
        } else {
          sourceCode = node.textContent;
        }

        pre.dataset.mermaidRendered = "1";

        var container = document.createElement("div");
        container.className = "mermaid";
        container.textContent = sourceCode;

        pre.replaceWith(container);
      });

    try {
      var runResult = mermaid.run({
        querySelector: ".mermaid"
      });

      if (runResult && typeof runResult.then === "function") {
        runResult.catch(function (error) {
          console.warn("Mermaid render skipped:", error);
        });
      }
    } catch (error) {
      console.warn("Mermaid initialization failed:", error);
    }
  }

  if (typeof document$ !== "undefined" && document$ && typeof document$.subscribe === "function") {
    document$.subscribe(function () {
      renderMermaid();
    });
    return;
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", renderMermaid);
  } else {
    renderMermaid();
  }
})();
