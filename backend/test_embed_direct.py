import os
from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.environ.get("NVIDIA_API_KEY")
)

# Try all possible input_type values
for itype in ["passage", "query", "search_document", "search_query", None]:
    try:
        kwargs = {
            "input": ["Hello world"],
            "model": "nvidia/nemotron-3-embed-1b",
            "encoding_format": "float",
        }
        if itype:
            kwargs["extra_body"] = {"input_type": itype}
        resp = client.embeddings.create(**kwargs)
        print(f"✅ input_type={itype!r} → dim={len(resp.data[0].embedding)}")
    except Exception as e:
        print(f"❌ input_type={itype!r} → {e}")
