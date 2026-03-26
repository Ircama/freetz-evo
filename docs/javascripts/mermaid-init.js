document$.subscribe(function() {
  if (typeof mermaid === "undefined") {
    return;
  }

  mermaid.initialize({
    startOnLoad: false,
    securityLevel: "loose",
    theme: "default"
  });

  document.querySelectorAll("pre code.language-mermaid, pre code.mermaid").forEach(function(code) {
    var pre = code.parentElement;
    if (!pre || pre.dataset.mermaidRendered === "1") {
      return;
    }

    pre.dataset.mermaidRendered = "1";

    var container = document.createElement("div");
    container.className = "mermaid";
    container.textContent = code.textContent;

    pre.replaceWith(container);
  });

  mermaid.run({
    querySelector: ".mermaid"
  });
});
