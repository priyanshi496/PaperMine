import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.environ.get("NVIDIA_API_KEY")
)

try:
    response = client.chat.completions.create(
        model="nvidia/nemotron-3-super-120b-a12b",
        temperature=0,
        messages=[{"role": "user", "content": "Return JSON: {\"hello\": \"world\"}"}],
        response_format={"type": "json_object"}
    )
    print("Success:", response.choices[0].message.content)
except Exception as e:
    print("Error:", repr(e))
