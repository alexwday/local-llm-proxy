#!/usr/bin/env python3
"""
Example client script demonstrating how to use the local LLM proxy
with the OpenAI Python library.

Install the OpenAI library first:
    pip install openai
"""

from openai import OpenAI

# Configure the client to use the local proxy
client = OpenAI(
    base_url="http://localhost:3000/v1",
    api_key="llm-proxy-09203315a5a42056b0e3ac769bfb22afa962ad52b790a78eb735595a45ba3c36"  # Replace with your token
)

def test_chat_completion():
    """Test the chat completion endpoint"""
    print("Testing chat completion...")

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "user", "content": "Hello, how are you?"}
        ]
    )

    print(f"Response: {response.choices[0].message.content}")
    print(f"Model: {response.model}")
    print(f"Tokens used: {response.usage.total_tokens}")
    print()

def test_list_models():
    """Test the models list endpoint"""
    print("Testing models list...")

    models = client.models.list()

    print("Available models:")
    for model in models.data:
        print(f"  - {model.id}")
    print()

if __name__ == "__main__":
    print("=" * 60)
    print("Local LLM Proxy - Example Client")
    print("=" * 60)
    print()

    test_list_models()
    test_chat_completion()

    print("=" * 60)
    print("Check the dashboard at http://localhost:3000")
    print("to see the logged API calls!")
    print("=" * 60)
