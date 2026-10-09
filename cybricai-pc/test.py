from google import genai

client = genai.Client(api_key="MY_SECRET_API")

print("Available models:")
for model in client.models.list():
    print(model.name)