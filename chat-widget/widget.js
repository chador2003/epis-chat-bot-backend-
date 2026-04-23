(function () {
  "use strict";

  var WIDGET_URL = "http://172.19.9.235:2000/chat-ui.html";
  // var WIDGET_URL = "https://epis-chat-widget.instatunnel.my/chat-ui.html";
  var BUBBLE_SIZE = 62;
  var BUBBLE_BOTTOM = 28;
  var BUBBLE_RIGHT = 28;
  var PRIMARY_COLOR = "#19b2ee";
  var PRIMARY_DARK = "#0d8abf";

  if (document.getElementById("epis-chat-root")) return; // prevent double init

  var style = document.createElement("style");
  style.textContent = [
    "#epis-chat-bubble{",
      "position:fixed;bottom:" + BUBBLE_BOTTOM + "px;right:" + BUBBLE_RIGHT + "px;",
      "width:" + BUBBLE_SIZE + "px;height:" + BUBBLE_SIZE + "px;",
      "background:linear-gradient(145deg," + PRIMARY_COLOR + "," + PRIMARY_DARK + ");",
      "border-radius:50%;display:flex;align-items:center;justify-content:center;",
      "cursor:pointer;z-index:2147483646;",
      "box-shadow:0 6px 24px rgba(25,178,238,.35);",
      "transition:transform .25s cubic-bezier(.34,1.56,.64,1),box-shadow .25s;",
      "animation:epis-pulse 3s ease-in-out infinite;",
    "}",
    "#epis-chat-bubble:hover{transform:scale(1.09);}",
    "#epis-chat-bubble.epis-active{",
      "background:linear-gradient(145deg,#e05555,#b83030);",
      "animation:none;box-shadow:0 6px 24px rgba(192,57,43,.35);",
    "}",
    "#epis-chat-bubble svg{width:26px;height:26px;fill:#fff;transition:transform .3s;}",
    "#epis-chat-bubble.epis-active svg{transform:rotate(90deg);}",
    "#epis-chat-frame{",
      "position:fixed;bottom:" + (BUBBLE_BOTTOM + BUBBLE_SIZE + 16) + "px;right:" + BUBBLE_RIGHT + "px;",
      "width:400px;height:650px;max-height:82vh;",
      "border:none;border-radius:22px;",
      "box-shadow:0 16px 56px rgba(13,34,51,.18),0 2px 8px rgba(0,0,0,.07);",
      "z-index:2147483645;",
      "opacity:0;transform:translateY(16px) scale(.96);pointer-events:none;",
      "transition:opacity .28s ease,transform .28s cubic-bezier(.34,1.2,.64,1);",
      "background:transparent;",
    "}",
    "#epis-chat-frame.epis-open{opacity:1;transform:translateY(0) scale(1);pointer-events:auto;}",
    "@media(max-width:768px){",
      "#epis-chat-frame{width:100vw;height:100vh;max-height:100%;bottom:0;right:0;border-radius:0;}",
    "}",
    "@keyframes epis-pulse{",
      "0%,100%{box-shadow:0 6px 24px rgba(25,178,238,.35),0 0 0 0 rgba(25,178,238,.28);}",
      "50%{box-shadow:0 6px 24px rgba(25,178,238,.35),0 0 0 11px rgba(25,178,238,0);}",
    "}",
  ].join("");
  document.head.appendChild(style);

  var root = document.createElement("div");
  root.id = "epis-chat-root";
  document.body.appendChild(root);

  var bubble = document.createElement("div");
  bubble.id = "epis-chat-bubble";
  bubble.setAttribute("role", "button");
  bubble.setAttribute("aria-label", "Open ePIS chat assistant");
  bubble.setAttribute("tabindex", "0");
  bubble.innerHTML = chatIcon();
  root.appendChild(bubble);

  var frame = document.createElement("iframe");
  frame.id = "epis-chat-frame";
  frame.src = WIDGET_URL;
  frame.title = "ePIS Chat Assistant";
  // frame.setAttribute("allow", "");
  root.appendChild(frame);

  var isOpen = false;
  function toggle() {
    isOpen = !isOpen;
    if (isOpen) {
      frame.classList.add("epis-open");
      bubble.classList.add("epis-active");
      bubble.innerHTML = closeIcon();
      bubble.setAttribute("aria-label", "Close ePIS chat assistant");
    } else {
      frame.classList.remove("epis-open");
      bubble.classList.remove("epis-active");
      bubble.innerHTML = chatIcon();
      bubble.setAttribute("aria-label", "Open ePIS chat assistant");
    }
  }

  bubble.addEventListener("click", toggle);
  bubble.addEventListener("keydown", function (e) {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(); }
  });

  // CLOSE FROM IFRAME
  window.addEventListener("message", function (e) {
    if (e.data === "epis:close") toggle();
  });

  //ICONS
  function chatIcon() {
    return '<svg viewBox="0 0 24 24"><path d="M12 3C6.48 3 2 6.92 2 12c0 2.38 1.05 4.52 2.81 6.17L4 22l4.2-1.82c1.04.29 2.13.45 3.27.45 5.52 0 10-3.92 10-9s-4.48-9-10-9z"/></svg>';
  }
  function closeIcon() {
    return '<svg viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>';
  }
})();