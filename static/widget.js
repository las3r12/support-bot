class BotWidget extends HTMLElement {
    constructor() {
        super();
        const shadow = this.attachShadow({ mode: 'open' });
        shadow.innerHTML = `
            <div class="chat-container">
                <div class="response-window"></div>
                <div class="input-area">
                    <input type="text" placeholder="Type a message..." />
                    <button>Send</button>
                </div>
            </div>
            <style>
            .chat-container {
                width: 300px;
                height: 200px;
                background-color: #f0f0f0;
                border-radius: 8px;
                border: 1px solid #ccc;
                position: fixed;
                right: 20px;
                bottom: 20px;
                display: flex;
                flex-direction: column;
            }
            .input-area {
                display: flex;
                padding: 8px;
                gap: 8px;
            }
            .response-window {
                flex: 1;
                overflow-y: auto;
                padding: 10px;
                overscroll-behavior: contain;
            }
            </style>
        `;
    }

    connectedCallback() {
        const shadow = this.shadowRoot;
        const sendBtn = shadow.querySelector("button");
        const input = shadow.querySelector("input");
        const responseWindow = shadow.querySelector(".response-window");
        sendBtn.addEventListener("click", () => this.sendMessage(input, responseWindow));
    }

    async sendMessage(input, responseWindow) {
         try {
                const msgDiv = document.createElement("div");
                msgDiv.classList.add("message");
                msgDiv.textContent = `You: ${input.value.trim()}`;
                responseWindow.appendChild(msgDiv);
                responseWindow.scrollTop = responseWindow.scrollHeight;

            const res = await fetch("http://localhost:5000/ask_question", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ 
                    "question" : input.value.trim(),
                    "token" : this.getAttribute("token")
                })
            });

            const data = await res.json();
            if(res.ok){
                const botMsg = document.createElement("div");
                botMsg.classList.add("message");
                botMsg.textContent = `-> ${data.answer}`;
                responseWindow.appendChild(botMsg);
                responseWindow.scrollTop = responseWindow.scrollHeight;
            } else {
                const botMsg = document.createElement("div");
                botMsg.classList.add("message");
                botMsg.textContent = `${data.error || "An error occurred"}`;
                responseWindow.appendChild(botMsg);
                responseWindow.scrollTop = responseWindow.scrollHeight;
            }
        } catch(err){
                const botMsg = document.createElement("div");
                botMsg.classList.add("message");
                botMsg.textContent = `Network error`;
                responseWindow.appendChild(botMsg);
                responseWindow.scrollTop = responseWindow.scrollHeight;
        }
        input.value = "";
    }
}


document.addEventListener("DOMContentLoaded", () => {
    customElements.define("bot-widget", BotWidget);
});