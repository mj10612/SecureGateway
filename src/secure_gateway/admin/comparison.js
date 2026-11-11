/**
 * ComparisonView component for SecureGateway admin UI (#342 / #343).
 *
 * Self-contained, accessible, zero-innerHTML side-by-side text diff component.
 * Renders aligned spans between original text and masked results.
 * Distinguishes changes without color (borders and index badges).
 * Provides synchronized scrolling, change navigation, search, and clipboard copy.
 */

"use strict";

(function (global) {
  function el(tag, text, className) {
    const node = document.createElement(tag);
    if (text !== undefined && text !== null) {
      node.textContent = text;
    }
    if (className) {
      node.className = className;
    }
    return node;
  }

  function renderComparisonView(container, options) {
    if (!container) return;
    container.replaceChildren();

    const original = options.original || "";
    const masked = options.masked || "";
    const spans = options.spans || [];
    const uncertain = Boolean(options.uncertain);

    let activeSpanIndex = -1;
    let originalSpanElements = [];
    let maskedSpanElements = [];

    // Outer wrapper
    const root = el("div", undefined, "diff-root");

    // Toolbar
    const toolbar = el("div", undefined, "diff-toolbar");

    // Navigation group
    const navGroup = el("div", undefined, "diff-nav-group");
    const countLabel = el(
      "span",
      uncertain
        ? "대응 불확실 (강조 생략)"
        : spans.length === 0
        ? "치환 없음"
        : `변경 ${spans.length}건`,
      "diff-count-label"
    );
    countLabel.setAttribute("role", "status");

    const prevButton = el("button", "↑ 이전 변경", "secondary diff-btn");
    prevButton.type = "button";
    prevButton.disabled = spans.length === 0 || uncertain;
    prevButton.setAttribute("aria-label", "이전 변경 구간으로 이동");

    const nextButton = el("button", "↓ 다음 변경", "secondary diff-btn");
    nextButton.type = "button";
    nextButton.disabled = spans.length === 0 || uncertain;
    nextButton.setAttribute("aria-label", "다음 변경 구간으로 이동");

    navGroup.append(countLabel, prevButton, nextButton);

    // Tools group (Search & Copy)
    const toolsGroup = el("div", undefined, "diff-tools-group");

    const searchInput = el("input", undefined, "diff-search-input");
    searchInput.type = "search";
    searchInput.placeholder = "텍스트 검색…";
    searchInput.setAttribute("aria-label", "원문 및 치환 결과 내 검색");

    const copyButton = el("button", "치환 결과 복사", "secondary diff-btn");
    copyButton.type = "button";
    copyButton.setAttribute("aria-label", "치환 결과를 클립보드에 복사");

    toolsGroup.append(searchInput, copyButton);
    toolbar.append(navGroup, toolsGroup);
    root.append(toolbar);

    // Uncertain banner if spans could not be verified safely
    if (uncertain) {
      const banner = el(
        "div",
        "구간 대응 불확실: 변환 위치를 안전하게 일치시킬 수 없어 강조 표시를 생략했습니다. 원문과 치환 결과 텍스트 자체는 안전하게 제공됩니다.",
        "diff-uncertain-banner"
      );
      banner.setAttribute("role", "alert");
      root.append(banner);
    }

    // Split container (side-by-side or stacked on mobile)
    const split = el("div", undefined, "diff-split");

    // Original Pane
    const origPane = el("div", undefined, "diff-pane diff-pane-original");
    const origHeader = el("div", undefined, "diff-pane-header");
    origHeader.append(el("h3", "원문 (입력)"), el("small", "로컬 명시 확인"));
    const origContent = el("pre", undefined, "diff-content");
    origContent.setAttribute("tabindex", "0");
    origContent.setAttribute("aria-label", "원문 텍스트");
    origPane.append(origHeader, origContent);

    // Masked Pane
    const maskPane = el("div", undefined, "diff-pane diff-pane-masked");
    const maskHeader = el("div", undefined, "diff-pane-header");
    maskHeader.append(el("h3", "치환 결과 (마스킹)"), el("small", "전송될 형태"));
    const maskContent = el("pre", undefined, "diff-content");
    maskContent.setAttribute("tabindex", "0");
    maskContent.setAttribute("aria-label", "치환 결과 텍스트");
    maskPane.append(maskHeader, maskContent);

    split.append(origPane, maskPane);
    root.append(split);

    // Build highlighted DOM nodes safely using textContent / createTextNode
    if (spans.length === 0 || uncertain) {
      origContent.textContent = original;
      maskContent.textContent = masked;
    } else {
      // Build original pane
      let oCursor = 0;
      originalSpanElements = [];
      spans.forEach((span, idx) => {
        if (span.original_start > oCursor) {
          origContent.appendChild(
            document.createTextNode(original.slice(oCursor, span.original_start))
          );
        }
        const spanNode = el(
          "mark",
          original.slice(span.original_start, span.original_end),
          "diff-span diff-span-orig"
        );
        spanNode.setAttribute("data-span-index", String(idx));
        spanNode.setAttribute("tabindex", "0");
        spanNode.setAttribute("role", "mark");
        spanNode.setAttribute(
          "aria-label",
          `변경 ${idx + 1}: ${span.alias}로 치환됨`
        );

        // Badge indicator for non-color identification
        const badge = el("span", `[${idx + 1}]`, "diff-badge");
        spanNode.prepend(badge);

        origContent.appendChild(spanNode);
        originalSpanElements.push(spanNode);
        oCursor = span.original_end;
      });
      if (oCursor < original.length) {
        origContent.appendChild(document.createTextNode(original.slice(oCursor)));
      }

      // Build masked pane
      let mCursor = 0;
      maskedSpanElements = [];
      spans.forEach((span, idx) => {
        if (span.masked_start > mCursor) {
          maskContent.appendChild(
            document.createTextNode(masked.slice(mCursor, span.masked_start))
          );
        }
        const spanNode = el(
          "mark",
          masked.slice(span.masked_start, span.masked_end),
          "diff-span diff-span-mask"
        );
        spanNode.setAttribute("data-span-index", String(idx));
        spanNode.setAttribute("tabindex", "0");
        spanNode.setAttribute("role", "mark");
        spanNode.setAttribute(
          "aria-label",
          `변경 ${idx + 1}: 원문 치환됨 (${span.alias})`
        );

        const badge = el("span", `[${idx + 1}]`, "diff-badge");
        spanNode.prepend(badge);

        maskContent.appendChild(spanNode);
        maskedSpanElements.push(spanNode);
        mCursor = span.masked_end;
      });
      if (mCursor < masked.length) {
        maskContent.appendChild(document.createTextNode(masked.slice(mCursor)));
      }
    }

    // Interactive linked highlight handling
    function activateSpan(index, scrollIntoView = false) {
      if (activeSpanIndex >= 0) {
        if (originalSpanElements[activeSpanIndex]) {
          originalSpanElements[activeSpanIndex].classList.remove("active");
        }
        if (maskedSpanElements[activeSpanIndex]) {
          maskedSpanElements[activeSpanIndex].classList.remove("active");
        }
      }
      activeSpanIndex = index;
      if (activeSpanIndex >= 0) {
        const oNode = originalSpanElements[activeSpanIndex];
        const mNode = maskedSpanElements[activeSpanIndex];
        if (oNode) oNode.classList.add("active");
        if (mNode) mNode.classList.add("active");
        if (scrollIntoView) {
          if (oNode) oNode.scrollIntoView({ block: "center", behavior: "smooth" });
          if (mNode) mNode.scrollIntoView({ block: "center", behavior: "smooth" });
        }
      }
    }

    [originalSpanElements, maskedSpanElements].forEach((list) => {
      list.forEach((node) => {
        const idx = Number(node.getAttribute("data-span-index"));
        node.addEventListener("mouseenter", () => activateSpan(idx));
        node.addEventListener("focus", () => activateSpan(idx));
        node.addEventListener("mouseleave", () => {
          if (activeSpanIndex === idx) activateSpan(-1);
        });
        node.addEventListener("blur", () => {
          if (activeSpanIndex === idx) activateSpan(-1);
        });
      });
    });

    // Next / Previous Navigation
    prevButton.addEventListener("click", () => {
      if (spans.length === 0) return;
      let target = activeSpanIndex <= 0 ? spans.length - 1 : activeSpanIndex - 1;
      activateSpan(target, true);
    });

    nextButton.addEventListener("click", () => {
      if (spans.length === 0) return;
      let target = activeSpanIndex >= spans.length - 1 ? 0 : activeSpanIndex + 1;
      activateSpan(target, true);
    });

    // Synchronized scrolling with loop guard
    let isSyncing = false;
    function syncScroll(source, target) {
      if (isSyncing) return;
      isSyncing = true;
      const percentage = source.scrollTop / Math.max(1, source.scrollHeight - source.clientHeight);
      target.scrollTop = percentage * (target.scrollHeight - target.clientHeight);
      setTimeout(() => {
        isSyncing = false;
      }, 30);
    }

    origContent.addEventListener("scroll", () => syncScroll(origContent, maskContent));
    maskContent.addEventListener("scroll", () => syncScroll(maskContent, origContent));

    // Copy result (explicit click only)
    copyButton.addEventListener("click", async () => {
      try {
        if (navigator.clipboard && navigator.clipboard.writeText) {
          await navigator.clipboard.writeText(masked);
        } else {
          const textarea = document.createElement("textarea");
          textarea.value = masked;
          document.body.appendChild(textarea);
          textarea.select();
          document.execCommand("copy");
          document.body.removeChild(textarea);
        }
        const originalText = copyButton.textContent;
        copyButton.textContent = "복사 완료 ✓";
        setTimeout(() => {
          copyButton.textContent = originalText;
        }, 2000);
      } catch (_) {
        copyButton.textContent = "복사 실패 ✕";
      }
    });

    // Search filter across text panes
    searchInput.addEventListener("input", () => {
      const query = searchInput.value.trim().toLowerCase();
      [originalSpanElements, maskedSpanElements].forEach((list) => {
        list.forEach((node) => {
          node.classList.remove("search-match");
          if (query && node.textContent.toLowerCase().includes(query)) {
            node.classList.add("search-match");
          }
        });
      });
    });

    container.appendChild(root);
  }

  global.ComparisonView = {
    render: renderComparisonView,
  };
})(typeof window !== "undefined" ? window : globalThis);
