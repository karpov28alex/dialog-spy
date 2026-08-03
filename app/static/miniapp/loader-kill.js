(() => {
  'use strict';

  const removeLegacyLoaders = root => {
    if (!root) return;
    if (root.nodeType === 1 && root.classList?.contains('ph-load')) {
      root.remove();
      return;
    }
    root.querySelectorAll?.('.ph-load').forEach(node => node.remove());
  };

  const originalAppendChild = Node.prototype.appendChild;
  Node.prototype.appendChild = function phantomAppendChild(node) {
    if (node?.nodeType === 1 && node.classList?.contains('ph-load')) {
      return node;
    }
    return originalAppendChild.call(this, node);
  };

  const originalAppend = Element.prototype.append;
  Element.prototype.append = function phantomAppend(...nodes) {
    const safe = nodes.filter(node => !(node?.nodeType === 1 && node.classList?.contains('ph-load')));
    return originalAppend.apply(this, safe);
  };

  const originalPrepend = Element.prototype.prepend;
  Element.prototype.prepend = function phantomPrepend(...nodes) {
    const safe = nodes.filter(node => !(node?.nodeType === 1 && node.classList?.contains('ph-load')));
    return originalPrepend.apply(this, safe);
  };

  const observer = new MutationObserver(records => {
    for (const record of records) {
      for (const node of record.addedNodes) removeLegacyLoaders(node);
    }
  });

  const start = () => {
    removeLegacyLoaders(document);
    observer.observe(document.documentElement, {childList: true, subtree: true});
    window.setInterval(() => removeLegacyLoaders(document), 500);
  };

  if (document.documentElement) start();
  else document.addEventListener('DOMContentLoaded', start, {once: true});
})();