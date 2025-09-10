# azure_test.py - Fixed for OpenAI >= 1.0.0

import os
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

# Azure OpenAI Configuration
AZURE_API_KEY = "3b3d56fe7c6c4809bdc73a725008b4ac"
AZURE_API_BASE = "https://autobugopenai.openai.azure.com/"
AZURE_DEPLOYMENT_NAME = "gpt-4o"
AZURE_API_VERSION = "2024-02-01"

def test_azure_connection():
    """Test Azure OpenAI connection with new API format."""
    try:
        # Initialize Azure OpenAI client (new format)
        client = AzureOpenAI(
            api_key=AZURE_API_KEY,
            api_version=AZURE_API_VERSION,
            azure_endpoint=AZURE_API_BASE,
        )
        
        print("🔄 Testing Azure OpenAI connection...")
        
        # Test API call
        response = client.chat.completions.create(
            model=AZURE_DEPLOYMENT_NAME,
            messages=[
                {"role": "user", "content": "Say 'Hello, Azure OpenAI is working!'"}
            ],
            max_tokens=50,
            temperature=0.7
        )
        
        result = response.choices[0].message.content
        print(f"✅ Success! Response: {result}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to connect: {str(e)}")
        return False

def test_configuration():
    """Test configuration values."""
    print("\n📋 Configuration Check:")
    print(f"API Key: {'✅ Set' if AZURE_API_KEY else '❌ Missing'}")
    print(f"Endpoint: {AZURE_API_BASE}")
    print(f"Deployment: {AZURE_DEPLOYMENT_NAME}")
    print(f"API Version: {AZURE_API_VERSION}")

if __name__ == "__main__":
    test_configuration()
    test_azure_connection()