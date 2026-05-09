"""Test Azure OpenAI connection to diagnose authentication issues."""
import os
from openai import AzureOpenAI
from azure.identity import ClientSecretCredential, get_bearer_token_provider
from dotenv import load_dotenv

# Load environment
load_dotenv()

print("="*60)
print("Azure OpenAI Connection Test")
print("="*60)

# Display configuration
endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
api_version = os.getenv("OPENAI_API_VERSION")
deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
tenant_id = os.getenv("TECHDEMO_TENANT_ID")
client_id = os.getenv("TECHDEMO_CLIENT_ID")
client_secret = os.getenv("TECHDEMO_CLIENT_SECRET")

print(f"\nConfiguration:")
print(f"  Endpoint: {endpoint}")
print(f"  API Version: {api_version}")
print(f"  Deployment: {deployment}")
print(f"  Tenant ID: {tenant_id[:10]}...{tenant_id[-4:] if tenant_id else 'None'}")
print(f"  Client ID: {client_id[:10]}...{client_id[-4:] if client_id else 'None'}")
print(f"  Client Secret: {'*' * 10}...{client_secret[-4:] if client_secret else 'None'}")

if not all([endpoint, api_version, deployment, tenant_id, client_id, client_secret]):
    print("\n❌ ERROR: Missing required configuration")
    exit(1)

print("\n" + "="*60)
print("Testing connection with Azure AD authentication...")
print("="*60)

try:
    # Create Azure AD credential
    scope = "https://cognitiveservices.azure.com/.default"
    credential = ClientSecretCredential(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret
    )
    token_provider = get_bearer_token_provider(credential, scope)
    
    print("\n✓ Azure AD credential created successfully")
    
    # Create client with Azure AD authentication
    client = AzureOpenAI(
        azure_endpoint=endpoint,
        api_version=api_version,
        azure_ad_token_provider=token_provider
    )
    
    print("\n✓ Client created successfully")
    
    # Try a simple completion
    print(f"\nTrying deployment: {deployment}")
    response = client.chat.completions.create(
        model=deployment,
        messages=[{"role": "user", "content": "Say 'test successful'"}],
        max_tokens=10
    )
    
    print(f"\n✅ SUCCESS!")
    print(f"Response: {response.choices[0].message.content}")
    print(f"\nYour Azure OpenAI connection is working correctly!")
    
except Exception as e:
    print(f"\n❌ ERROR: {type(e).__name__}")
    print(f"Message: {str(e)}")
    print(f"\nTroubleshooting:")
    print(f"  1. Verify API key is correct")
    print(f"  2. Check endpoint URL is correct")
    print(f"  3. Verify deployment name '{deployment}' exists in your Azure OpenAI resource")
    print(f"  4. Ensure subscription is active")
    print(f"  5. Try common deployment names: gpt-4, gpt-35-turbo, gpt-4-32k")
    
    # Suggest trying different deployment names
    common_deployments = ["gpt-4", "gpt-35-turbo", "gpt-4-32k", "gpt-4o", "gpt-35-turbo-16k"]
    print(f"\n  Common deployment names to try:")
    for dep in common_deployments:
        print(f"    - {dep}")
    
    print(f"\n  To test a different deployment, update AZURE_OPENAI_DEPLOYMENT_NAME in .env")
