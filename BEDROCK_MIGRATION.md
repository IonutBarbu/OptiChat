# Migration to pydantic-ai BedrockConverseModel

## Summary of Changes

The AWS Bedrock integration has been migrated from using `boto3` directly to using pydantic-ai's native `BedrockConverseModel`. This provides a cleaner, more maintainable implementation that's consistent with the pydantic-ai framework.

## What Changed

### 1. Dependencies
**Before:**
- `boto3>=1.35.0` - Direct AWS SDK usage
- `pydantic-ai==0.0.43` - Basic pydantic-ai

**After:**
- `pydantic-ai[bedrock]==0.0.43` - Includes Bedrock support

### 2. Implementation
**Before:**
- Used `boto3.client('bedrock-runtime')` for API calls
- Separate code paths for Anthropic vs. non-Anthropic models
- Manual request/response handling
- Complex async/sync bridging

**After:**
- Uses `BedrockConverseModel` from pydantic-ai
- Unified code path for all Bedrock models
- Automatic request/response handling via pydantic-ai
- Simpler async/sync integration

### 3. BedrockLLMClient Class
**Key Changes:**
- Removed `boto3` client initialization
- Removed AWS credentials parameters (handled by AWS SDK automatically)
- Removed `region` parameter (uses AWS default configuration)
- Added `max_tokens` parameter for model settings
- Simplified to single `chat_completion` method (no more split paths)
- Uses `BedrockModelSettings` for configuration

### 4. Model Support
**Supported Models:**
- Claude Sonnet 4 (eu.anthropic.claude-sonnet-4-5-20250929-v1:0)
- GPT-OSS-20B (openai.gpt-oss-20b-1:0)
- GPT-OSS-120B (openai.gpt-oss-120b-1:0)

## Installation

```bash
# Install updated requirements
pip install -r requirements.txt

# Or install pydantic-ai with bedrock support directly
pip install 'pydantic-ai[bedrock]'
```

## AWS Configuration

pydantic-ai's `BedrockConverseModel` uses the standard AWS SDK credential chain:

1. **Environment Variables** (recommended for local development):
   ```bash
   export AWS_REGION=us-east-1
   export AWS_ACCESS_KEY_ID=your_access_key
   export AWS_SECRET_ACCESS_KEY=your_secret_key
   ```

2. **AWS CLI Configuration**:
   ```bash
   aws configure
   ```

3. **AWS Profile** (if using named profiles):
   ```bash
   export AWS_PROFILE=your-profile-name
   ```

4. **IAM Role** (for EC2/ECS deployments) - automatic

**No code changes needed** - the AWS SDK handles authentication automatically!

## Usage

No changes to the public API. Usage remains the same:

```python
from llm_client import LLMClientFactory, UnifiedLLMClient

# Create Bedrock client
llm_client = LLMClientFactory.create_client(
    provider="bedrock",
    model_name="gpt-oss-120b"
)

# Wrap for backward compatibility
client = UnifiedLLMClient(llm_client)

# Use normally
response = client.chat.completions.create(
    messages=[{"role": "user", "content": "Hello!"}],
    temperature=0.1
)
```

## Benefits of This Migration

1. **Simpler Code**: Removed ~200 lines of boto3-specific code
2. **Better Integration**: Fully leverages pydantic-ai's capabilities
3. **Automatic Retries**: pydantic-ai handles retries and error handling
4. **Type Safety**: Better type checking with pydantic models
5. **Future-Proof**: Easier to add new Bedrock features as pydantic-ai evolves
6. **Consistent API**: All model interactions go through pydantic-ai Agent

## Breaking Changes

### Removed Parameters
The following parameters are **no longer available** in `BedrockLLMClient.__init__()`:
- `region` - Use AWS SDK configuration instead
- `aws_access_key_id` - Use AWS SDK configuration instead
- `aws_secret_access_key` - Use AWS SDK configuration instead

### Migration Path
If you were passing these parameters explicitly:

**Before:**
```python
client = BedrockLLMClient(
    model_name="gpt-oss-120b",
    region="eu-west-1",
    aws_access_key_id="AKIA...",
    aws_secret_access_key="..."
)
```

**After:**
```python
# Set credentials via environment or AWS CLI
os.environ['AWS_REGION'] = 'eu-west-1'
# OR: aws configure

# Then create client without credentials
client = BedrockLLMClient(
    model_name="gpt-oss-120b"
)
```

### New Parameters
Added parameter:
- `max_tokens` (default: 4096) - Controls maximum response length

## Testing

Test the migration:

```bash
# Set AWS credentials
export AWS_REGION=us-east-1
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret

# Or use AWS profile
export AWS_PROFILE=your-profile

# Run the app
streamlit run app.py
```

In the UI:
1. Select "bedrock" provider
2. Choose a model (e.g., "gpt-oss-120b")
3. Upload an optimization model
4. Test queries

## Troubleshooting

### Error: "BedrockConverseModel not available"
**Solution**: Install pydantic-ai with bedrock support:
```bash
pip install 'pydantic-ai[bedrock]'
```

### Error: "Unable to locate credentials"
**Solution**: Configure AWS credentials:
```bash
aws configure
# OR
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
```

### Error: "Could not connect to the endpoint URL"
**Solution**: Check AWS region is correct:
```bash
export AWS_REGION=us-east-1  # or your preferred region
```

### Error: "Access Denied"
**Solution**: Ensure model access is enabled in AWS Bedrock console

## Performance Comparison

Initial testing shows:
- **Similar latency** to boto3 implementation
- **Better error handling** via pydantic-ai
- **Automatic retries** on transient failures
- **Cleaner error messages**

## Future Enhancements

With this migration, we can now easily add:
- Streaming support with proper async handling
- Tool/function calling via pydantic-ai's native support
- Structured output with Pydantic models
- Conversation history management
- Cost tracking via pydantic-ai's usage metrics

## Rollback

If needed, rollback to the previous boto3 implementation:

```bash
git revert <commit-hash>
pip install boto3>=1.35.0
```

## Support

For issues or questions:
1. Check AWS credentials configuration
2. Verify model access in AWS Bedrock console
3. Check pydantic-ai documentation: https://ai.pydantic.dev/
4. Review error messages and stack traces

## Credits

Implementation inspired by the Alliander AIES Agent example, which demonstrates best practices for using pydantic-ai with AWS Bedrock.
