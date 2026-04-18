import socket
import json
import ssl
import secrets


class LLMClient:
    def __init__(self, max_context_len: int, token: str, model: str = "nvidia/nemotron-3-nano-30b-a3b:free", ):
        self.token = token
        self.model = model
        self._hostname = "openrouter.ai"
        self._path = "/api/v1/chat/completions"
        self._max_context_len = max_context_len

    def get_answer(self, question: str, history: str, key: str, db) -> dict:
        with open("resources/prompt.txt", 'r') as f:
            system_prompt = f.read()

        chunks = db.retrieve(key, question)
        if not chunks:
            context = db.get_all_text(key)
        else:
            context = "\n\n".join(chunks)
            print(chunks)

        def build_prompt(ctx):
            raw_text = "=== DATA START ===\n" + ctx + "\n=== DATA END ===\n" \
                + "=== MESSAGE HISTORY START ===\n" + history + "\n=== MESSAGE HISTORY END ===" \
                + "=== QUESTION START ===\n" + question + "\n=== QUESTION END ==="
            wrapped_text = self._wrap(raw_text, system_prompt)
            return system_prompt + "\n" + wrapped_text

        resp = self._complete(build_prompt(context))
        if resp['status'] == 'fallback' and chunks:
            resp = self._complete(build_prompt(db.get_all_text(key)))
        return resp

    def _wrap(self, data: str, prompt: str) -> str:
        nonce = self._generate_nonce()
        open_tag = f"<DATA_{nonce}>\n"
        close_tag = f"\n</DATA_{nonce}>"
        overhead = len(open_tag) + len(close_tag) + len(prompt)
        available = self._max_context_len - overhead
        if available <= 0:
            raise ValueError("Context length too small for wrapping overhead and prompt")
        if len(data) > available:
            data = data[:available]
        return open_tag + data + close_tag


    def _complete(self, prompt: str) -> dict:
        payload = json.dumps({
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}]
        })
        response = self._post(payload)
        return json.loads(json.loads(response)['choices'][0]['message']['content'])

    def _post(self, data: str) -> str:
        body = data.encode()
        header_str = (
            f"POST {self._path} HTTP/1.1\r\n"
            f"Host: {self._hostname}\r\n"
            f"Content-Type: application/json\r\n"
            f"Content-Length: {len(body)}\r\n"
            f"Authorization: Bearer {self.token}\r\n"
            f"Connection: close\r\n"
            "\r\n"
        )
        request = header_str.encode() + body
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        context = ssl.create_default_context()
        sock = context.wrap_socket(sock, server_hostname=self._hostname)
        try:
            sock.connect((self._hostname, 443))
            sock.sendall(request)
            resp = b""
            while chunk := sock.recv(1024):
                resp += chunk
        finally:
            sock.close()
        _, _, body_raw = resp.partition(b"\r\n\r\n")
        return self._decode_chunked(body_raw)

    def _decode_chunked(self, data: bytes) -> str:
        body = b""
        while data:
            size_line, _, data = data.partition(b"\r\n")
            size = int(size_line.strip(), 16)
            if size == 0:
                break
            body += data[:size]
            data = data[size + 2:]
        return body.decode()
    
    def _generate_nonce():
        chars = "abcdefghijklmnopqrstuvwxyz0123456789"
        return "".join(secrets.choice(chars) for _ in range(8))
    

