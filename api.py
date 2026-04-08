import socket
import json
import ssl

def https_post(data, headers, hostname, path='/'):
    body = str(data).encode()
    headers_str = (
        f"POST {path} HTTP/1.1\r\n"
        f"Host: {hostname}\r\n"
        f"Content-Type: application/json\r\n"
        f"Content-Length: {len(body)}\r\n"
        f"Connection: close\r\n"
        + "".join(f"{k}: {v}\r\n" for k, v in headers.items())
        + "\r\n"
    )
    request = headers_str.encode() + body
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    context = ssl.create_default_context()
    sock = context.wrap_socket(sock, server_hostname=hostname)
    try:
        sock.connect((hostname, 443))
        sock.sendall(request)
        
        resp = b""
        while chunk := sock.recv(1024):
            resp += chunk
    finally:
        sock.close()
    _, _, body_raw = resp.partition(b"\r\n\r\n")
    data = decode_chunked(body_raw)
    return data

def decode_chunked(data: bytes) -> str:
    body = b""
    while data:
        size_line, _, data = data.partition(b"\r\n")
        size = int(size_line.strip(), 16)
        if size == 0:
            break
        body += data[:size]
        data = data[size + 2:]
    return body.decode()


def get_answer(question, history, key, db):
    text = ""
    token = ""
    with open("resources/prompt.txt", 'r') as f:
        system_prompt = f.read()
    with open('resources/config.json', 'r') as f:
        token = json.load(f)['llm_key']

    chunks = db.retrieve(key, question)
    if not chunks:
            context = db.get_all_text(key)
    else:
        context = "\n\n".join(chunks)
        print(chunks)

    text += system_prompt
    text += "=== DATA START ===\n" + context + "\n=== DATA END ===\n"
    text += "=== MESSAGE HISTORY START ===\n" + history + "\n=== MESSAGE HISTORY END ==="
    text += "=== QUESTION START ===\n" + question + "\n=== QUESTION END ==="
    resp = get_llm_anser(text, token)
    if resp['status'] == 'fallback' and chunks:
        text = system_prompt
        text += "=== DATA START ===\n" + db.get_all_text(key) + "\n=== DATA END ===\n"
        text += "=== MESSAGE HISTORY START ===\n" + history + "\n=== MESSAGE HISTORY END ==="
        text += "=== QUESTION START ===\n" + question + "\n=== QUESTION END ==="
    resp = get_llm_anser(text, token)
    return resp

def get_llm_anser(prompt, token):
    data = json.dumps({
        "model": "nvidia/nemotron-3-nano-30b-a3b:free",
        "messages": [
        {
            "role": "user",
            "content": prompt
        }
        ]
    })
    response = https_post(data=data, hostname="openrouter.ai", path="/api/v1/chat/completions", headers={
        "Authorization": f"Bearer {token}"
    })
    resp = json.loads(json.loads(response)['choices'][0]['message']['content'])
    return resp

