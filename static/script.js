async function sendMessage() {
  const input = document.getElementById("user-input");
  const message = input.value.trim();
  if (!message) return;

  addMessage("You", message, "user");
  input.value = "";

  const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
          message: message,
          user_id: "user1"
      })
  });

  const data = await response.json();
  addMessage("ShadeMate", data.reply, "bot");
}

function addMessage(sender, text, cssClass) {
  const chatBox = document.getElementById("chat-box");
  const message = document.createElement("div");
  message.classList.add("message", cssClass);
  message.innerHTML = `<strong>${sender}:</strong> ${text}`;
  chatBox.appendChild(message);
  chatBox.scrollTop = chatBox.scrollHeight;
}
