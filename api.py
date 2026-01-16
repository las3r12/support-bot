import requests
import json
from db import get_text

def get_answer(question, user_id):
    text = ""
    token = ""
    with open("resources/prompt.txt", 'r') as f:
        text = f.read()
    with open('resources/config.json', 'r') as f:
        token = json.load(f)['llm_key']
    text += "=== DATA START ===\n" + get_text(user_id) + "\n=== DATA END ===\n"
    text += "=== QUESTION START ===\n" + question + "\n=== QUESTION END ==="
    response = requests.post(
    url="https://openrouter.ai/api/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {token}"
    },
    data=json.dumps({
        "model": "nvidia/nemotron-3-nano-30b-a3b:free",
        "messages": [
        {
            "role": "user",
            "content": text
        }
        ]
    })
    )
    print(response.text)
    return json.loads(response.text)['choices'][0]['message']['content']

