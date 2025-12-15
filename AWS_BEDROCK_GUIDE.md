# AWS Bedrock Integration Guide

## Overview

OptiChat now supports AWS Bedrock as an LLM provider alongside OpenAI. This integration uses the `pydantic-ai` framework to communicate with Bedrock models, offering access to Claude Sonnet 4 and OpenAI GPT-OSS models available through AWS Bedrock.

## Features

- **Multiple Model Support**: Claude Sonnet 4, GPT-OSS-20B, GPT-OSS-120B
- **Unified Interface**: Seamless switching between OpenAI and Bedrock providers
- **Backward Compatibility**: Existing code continues to work without changes
- **Regional Flexibility**: Configure AWS regions as needed

## Prerequisites

1. **AWS Account** with Bedrock access
2. **AWS Credentials** configured
3. **Model Access** granted in AWS Bedrock console
4. **Python Dependencies**: `pydantic-ai` (included in requirements.txt)

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure AWS Credentials

Choose one of these methods:

#### Option A: Environment Variables

Create a `.env` file in the project root:

```bash
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
```

#### Option B: AWS CLI Configuration

```bash
aws sso login --profile wv-support-tst
export AWS_PROFILE=wv-support-tst
```

#### Option C: IAM Role (for EC2/ECS)

If running on AWS infrastructure, attach an IAM role with Bedrock permissions.

### 3. Grant Bedrock Model Access

1. Go to AWS Console → Amazon Bedrock
2. Navigate to "Model access" in the left sidebar
3. Click "Manage model access"
4. Enable access for the models you want to use:
   - Anthropic Claude Sonnet 4
   - OpenAI GPT-OSS-20B
   - OpenAI GPT-OSS-120B
5. Submit your request (approval is usually instant for most models)

### 4. Required IAM Permissions

Ensure your AWS credentials have these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/*"
      ]
    }
  ]
}
```

## Usage

### In OptiChat UI

1. Launch OptiChat:
   ```bash
   streamlit run app.py
   ```

2. In the sidebar:
   - **Provider**: Select "bedrock"
   - **Bedrock Model**: Choose your preferred model (e.g., "gpt-oss-120b")

3. Upload your optimization model and start chatting!

### Available Bedrock Models

OptiChat supports these Bedrock models out of the box:

| Friendly Name | Bedrock Model ID |
|---------------|------------------|
| claude-sonnet-4 | eu.anthropic.claude-sonnet-4-5-20250929-v1:0 |
| gpt-oss-20b | openai.gpt-oss-20b-1:0 |
| gpt-oss-120b | openai.gpt-oss-120b-1:0 |

### Programmatic Usage

```python
from llm_client import LLMClientFactory, UnifiedLLMClient

# Create Bedrock client
llm_client = LLMClientFactory.create_client(
    provider="bedrock",
    model_name="gpt-oss-120b"
)

# Wrap for backward compatibility
client = UnifiedLLMClient(llm_client)

# Use like any OpenAI client
completion = client.chat.completions.create(
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain optimization models."}
    ],
    temperature=0.1
)
```

## Troubleshooting

### Error: "The security token included in the request is invalid"

**Solutions**:
1. Check AWS credentials are correctly configured
2. Verify credentials haven't expired (temporary credentials expire)
3. Ensure correct AWS region is set
4. Try running `aws sts get-caller-identity` to verify credentials

### Error: "Access Denied" or "Model not found"

**Solutions**:
1. Enable model access in AWS Bedrock console (see step 3 in setup)
2. Verify your IAM user/role has bedrock:InvokeModel permissions
3. Check the model is available in your selected AWS region

### Error: "ValidationException: The provided model identifier is invalid"

**Solutions**:
1. Verify model ID is correct for your region
2. Some models use region-specific prefixes (e.g., `us.anthropic.claude-*` vs `anthropic.claude-*`)
3. Check model availability in your region via AWS console

### Models are slow or timing out

**Solutions**:
1. Check your AWS region latency (choose closer regions)
2. Verify Bedrock service is healthy in AWS status page
3. Some models have cold-start delays on first invocation

## Cost Considerations

AWS Bedrock pricing varies by model and region. Key points:

- **Claude Sonnet 4**: Premium pricing for highest capability
- **GPT-OSS-120B**: High-capacity open-source model
- **GPT-OSS-20B**: More economical option for simpler tasks

Check current pricing: https://aws.amazon.com/bedrock/pricing/

**Cost Optimization Tips**:
- Use GPT-OSS-20B for simpler queries
- Monitor usage with AWS CloudWatch
- Set up billing alerts in AWS
- Consider model prompt caching for repeated queries


## Architecture

### Components

1. **llm_client.py**: Abstraction layer for LLM providers
   - `LLMClient`: Abstract base class
   - `BedrockLLMClient`: AWS Bedrock implementation via pydantic-ai
   - `OpenAILLMClient`: OpenAI implementation
   - `UnifiedLLMClient`: Backward-compatible wrapper
   - `LLMClientFactory`: Provider-based client creation

2. **app.py**: UI with provider selection
3. **agents.py**: Multi-agent system (works with both providers)
4. **utils.py**: Workflow orchestration

### Message Flow

```
User Query → Streamlit UI → UnifiedLLMClient → BedrockLLMClient → pydantic-ai Agent → AWS Bedrock Runtime → Model Response
```

### Async/Sync Bridge

Pydantic-ai uses async patterns, but OptiChat is synchronous. The implementation:
- Detects if an event loop is running
- Uses ThreadPoolExecutor if needed
- Falls back to `asyncio.run()` otherwise

## Advanced Configuration

### Custom Model IDs

Add custom models to `BedrockLLMClient.MODEL_ID_MAP` in `llm_client.py`:

```python
MODEL_ID_MAP = {
    "my-custom-model": "custom.model-id-v1:0",
    # ... existing models
}
```

### Custom Region per Request

```python
llm_client = LLMClientFactory.create_client(
    provider="bedrock",
    model_name="claude-3-5-sonnet",
    region="eu-west-1"  # Override default region
)
```

## Comparison: OpenAI vs Bedrock

| Feature | OpenAI | AWS Bedrock |
|---------|--------|-------------|
| **Models** | GPT-4, GPT-3.5, O1 | Claude Sonnet 4, GPT-OSS-20B/120B |
| **Pricing** | Per-token usage | Per-token usage + AWS costs |
| **Setup** | API key only | AWS account + credentials |
| **Latency** | Generally faster | Varies by region |
| **Privacy** | OpenAI terms | AWS terms (potentially better for enterprise) |
| **Availability** | Global | Region-dependent |

## Support and Resources

- **AWS Bedrock Documentation**: https://docs.aws.amazon.com/bedrock/
- **Pydantic-AI Documentation**: https://ai.pydantic.dev/
- **OptiChat Issues**: [GitHub Issues](https://github.com/yourusername/OptiChat/issues)

## Future Enhancements

Planned features:
- Streaming support for real-time responses
- Model-specific temperature/parameter tuning
- Cost tracking and optimization
- Cross-region failover
- Prompt caching for Bedrock
