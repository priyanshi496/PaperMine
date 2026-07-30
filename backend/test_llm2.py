import os
from openai import OpenAI

# manual read env
with open(".env") as f:
    for line in f:
        if line.startswith("NVIDIA_API_KEY="):
            os.environ["NVIDIA_API_KEY"] = line.strip().split("=")[1]

nvidia_key = os.environ.get("NVIDIA_API_KEY")
print("Key length:", len(nvidia_key) if nvidia_key else None)

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=nvidia_key
)

try:
    print("Sending request to GLM-5.2...")
    response = client.chat.completions.create(
        model="z-ai/glm-5.2",
        temperature=0,
        messages=[{"role": "user", "content": "Hi"}],
    )
    print("Response:", response.choices[0].message.content)
except Exception as e:
    print("Error:", e)
