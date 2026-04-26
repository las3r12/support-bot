import socket
import json
import re
import ssl
import secrets
from json_repair import repair_json

class LLMClient:
    def __init__(self, token: str, max_context_len: int, model: str):
        self._token = token
        self._model = model
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
        def build_prompt(ctx):
            data_nonce = self._generate_nonce()
            history_nonce = self._generate_nonce()
            question_nonce = self._generate_nonce()

            history_block = self._wrap_tagged(history, "HISTORY", history_nonce)
            question_block = self._wrap_tagged(question, "QUESTION", question_nonce)

            filled_prompt = system_prompt \
                .replace("{{DATA_NONCE}}", data_nonce) \
                .replace("{{HISTORY_NONCE}}", history_nonce) \
                .replace("{{QUESTION_NONCE}}", question_nonce)

            overhead = len(filled_prompt) + len(history_block) + len(question_block)
            available = self._max_context_len - overhead
            if available <= 0:
                raise ValueError("Context length too small")
            data_block = self._wrap_tagged(ctx[:available], "DATA", data_nonce)

            return filled_prompt + "\n" + data_block + "\n" + history_block + "\n" + question_block

        resp = self._complete(build_prompt(context))
        
        if resp['status'] == 'fallback' and chunks:
            resp = self._complete(build_prompt(db.get_all_text(key)))
        return resp

    def _wrap_tagged(self, data: str, tag: str, nonce: str) -> str:
        return f"<{tag}_{nonce}>\n{data}\n</{tag}_{nonce}>"


    def _complete(self, prompt: str) -> dict:
        payload = json.dumps({
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
        })
        response = self._post(payload)
        try:
            content = json.loads(response)['choices'][0]['message']['content']
            return self.parse_llm_json(content)
        except Exception as e:
            print(f"LLM parse error: {e}\nRaw response: {response}")
            return {"status": "fallback", "response": None}


    def _post(self, data: str) -> str:
        body = data.encode()
        header_str = (
            f"POST {self._path} HTTP/1.1\r\n"
            f"Host: {self._hostname}\r\n"
            f"Content-Type: application/json\r\n"
            f"Content-Length: {len(body)}\r\n"
            f"Authorization: Bearer {self._token}\r\n"
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
        headers_raw, _, body_raw = resp.partition(b"\r\n\r\n")
        headers = headers_raw.decode(errors="replace").lower()
        if "transfer-encoding: chunked" in headers:
            return self._decode_chunked(body_raw)
        return body_raw.decode()

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
    
    def _generate_nonce(self):
        chars = "abcdefghijklmnopqrstuvwxyz0123456789"
        return "".join(secrets.choice(chars) for _ in range(8))
    
    def parse_llm_json(self, raw):
        cleaned = raw.strip().removeprefix("```json").removesuffix("```").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return json.loads(repair_json(cleaned))


