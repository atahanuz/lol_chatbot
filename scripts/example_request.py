from openai import OpenAI


API_KEY = "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"
client = OpenAI(api_key=API_KEY)

context_messages = [
    {"role": "system",  "content": "Soruya cevap ver "},
    {"role": "user", "content": "2+2 kaçtır?"}
]

response = client.chat.completions.create(
    model="gpt-4.1-mini",
    messages=context_messages
)
print(response.choices[0].message.content)