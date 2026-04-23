const API_URL = "http://172.19.9.235:9000/chat";
const sendBtn = document.getElementById("sendBtn");
const input = document.getElementById("user-input");
const messages = document.getElementById("chat-messages");
const now = new Date();

// Options to customize the output
const options = { 
  weekday: 'long', 
  year: 'numeric', 
  month: 'long', 
  day: 'numeric' 
};

const currentDate = now.toLocaleDateString('en-US', options);

marked.setOptions({
  breaks: true,
  gfm: true,
  sanitize: false,
});

function closeChat() {
  window.parent.postMessage("epis:close", "*");
}

/* MESSAGE HELPERS */
function addDateChip(label) {
  const chip = document.createElement("div");
  chip.className = "date-chip";
  chip.textContent = label;
  messages.appendChild(chip);
}

function addUserMessage(text) {
  const div = document.createElement("div");
  div.className = "message user";
  div.textContent = text;
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
  return div;
}

function addBotMessage(text) {
  const div = document.createElement("div");
  div.className = "message bot";
  div.innerHTML = marked.parse(text);
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
  return div;
}

// New helper: Create empty bot message that can be updated
function createBotMessage() {
  const div = document.createElement("div");
  div.className = "message bot";
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
  return div;
}

function updateBotMessage(div, text) {
  div.innerHTML = marked.parse(text);
  messages.scrollTop = messages.scrollHeight;
}

/* TYPING */
function showTypingDots() {
  const div = document.createElement("div");
  div.id = "typingDots";
  div.className = "message bot typing-indicator";
  div.innerHTML =
    '<div class="typing-dot"></div>\
<div class="typing-dot"></div>\
<div class="typing-dot"></div>';
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
}

function hideTypingDots() {
  const el = document.getElementById("typingDots");
  if (el) el.remove();
}

/* SEND MESSAGE */
sendBtn.addEventListener("click", sendMessage);
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    e.preventDefault();
    sendMessage();
  }
});

async function sendMessage() {
  const text = input.value.trim();
  if (!text) return;

  addUserMessage(text);
  input.value = "";
  input.disabled = true;
  sendBtn.disabled = true;
  showTypingDots();

  try {
    const res = await fetch(API_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        query: text
      }),
    });

    if (!res.ok) {
      throw new Error(`HTTP error! status: ${res.status}`);
    }

    hideTypingDots();

    // Handle streaming response
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let fullResponse = "";
    
    // Create bot message div to update progressively
    const botMessageDiv = createBotMessage();

    while (true) {
      const { done, value } = await reader.read();
      
      if (done) break;
      
      // Decode chunk and append to full response
      const chunk = decoder.decode(value, { stream: true });
      fullResponse += chunk;
      
      // Update the bot message with current response
      updateBotMessage(botMessageDiv, fullResponse);
    }

    // Final update (in case there's any remaining content)
    if (fullResponse.trim()) {
      updateBotMessage(botMessageDiv, fullResponse);
    } else {
      updateBotMessage(botMessageDiv, "I couldn't retrieve that information.");
    }

  } catch (err) {
    console.error("Fetch error:", err);
    hideTypingDots();
    addBotMessage("⚠️ Unable to connect to ePIS services. Error: " + err.message);
  } finally {
    input.disabled = false;
    sendBtn.disabled = false;
    input.focus();
  }
}

addDateChip(currentDate);

addBotMessage(`
👋 **Welcome to ePIS!** I'm here to help you navigate the **Electronic Patient Information System (EPIS)**.

**I can assist you with:**
* 📁 Navigation and menu paths
* 🔧 Troubleshooting errors and access issues
* 📋 Step-by-step procedures for clinical and administrative tasks
* 👥 Role-specific guidance (Doctors, Nurses, Pharmacists)

---

**To get started, simply tell me:**
* What module you need help with (e.g., Pharmacy, IPD, Reception)
* What task you're trying to complete

How can I help you with EPIS today?
`);