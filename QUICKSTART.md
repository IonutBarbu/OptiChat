# AWS Bedrock Integration - Quick Start Guide

## Implementation Status: ✅ COMPLETE

All code has been successfully implemented. Follow these steps to test the new AWS Bedrock integration.

## Step 1: Install Dependencies

dependencies (pydantic-ai, openai, streamlit, etc.) are in requirements.txt.

```bash
uv pip install -r requirements.txt 
```

## Step 2: Configure AWS Credentials

Choose one of these methods:

### Option A: Environment Variables (Recommended for Testing)

```bash
export AWS_REGION="us-east-1"
export AWS_ACCESS_KEY_ID="your_access_key"
export AWS_SECRET_ACCESS_KEY="your_secret_key"
```

### Option B: AWS CLI Configuration [PREFFERED]

```bash
aws sso login --profile wv-support-tst
export AWS_PROFILE=wv-support-tst
```

### Option C: .env File

Create a `.env` file in the project root:

```bash
cp .env.example .env
# Edit .env and add your AWS credentials
```

## Step 3: Enable Bedrock Model Access in AWS Console

1. Log in to AWS Console
2. Navigate to: **Amazon Bedrock** service
3. Click **Model access** in left sidebar
4. Click **Manage model access** button
5. Enable these models (recommended):
   - ✅ Anthropic Claude 3.5 Sonnet
   - ✅ Anthropic Claude 3 Haiku
   - ✅ Anthropic Claude 3 Opus
6. Click **Save changes**
7. Wait for status to change to "Access granted" (~1 minute)

## Step 4: Test OpenAI Provider (Verify No Breaking Changes)

```bash
# Ensure OpenAI key is set
export OPENAI_API_KEY="your_openai_key"

# Run the app
streamlit run app.py
```

**In the UI:**
1. Provider: Select **"openai"**
2. Model: Select **"gpt-4-turbo-preview"**
3. Upload a model from `Feas/` folder (e.g., `Feas/diet.py`)
4. Click **Process**
5. Try a query: "What are the decision variables in this model?"
6. ✅ Verify it works as before

## Step 5: Test AWS Bedrock Provider (New Feature)

**In the same UI session:**
1. Provider: Switch to **"bedrock"**
2. Model: Select **"gpt-oss-120b"**
3. The model is already loaded (no need to re-upload)
4. Try a query: "Explain the objective function"
5. ✅ Verify Bedrock response appears

**Expected Behavior:**
- Provider switch should be seamless
- Model list updates when provider changes
- Bedrock responses may be slightly slower on first call (cold start)
- All OptiChat features should work identically

## Step 6: Test All Query Types

Test each query type with Bedrock:

### Retrieval Query
```
What are all the constraints in this model?
```

### Diagnosing Query (use an infeasible model)
```
Why is this model infeasible?
```

### Sensitivity Query
```
How sensitive is the objective to changes in the demand parameter?
```

### What-If Query
```
What if we increase the budget by 20%?
```

### Why-Not Query
```
Why can't the production be increased to 500 units?
```

## Step 7: Test Model Switching

1. Try different Bedrock models:
   - **gpt-oss-120b** (high-capacity, default)
   - **gpt-oss-20b** (faster, more economical)
   - **claude-sonnet-4** (highest intelligence)

2. Compare responses and performance

## Troubleshooting

### Error: "The security token included in the request is invalid"
**Fix**: Check AWS credentials
```bash
aws sts get-caller-identity  # Verify credentials work
```

### Error: "Access Denied" or "ValidationException"
**Fix**: Enable model access in AWS Bedrock console (Step 3 above)

### Error: "Could not import pydantic_ai"
**Fix**: Reinstall dependencies
```bash
pip install -r requirements.txt
```

### Bedrock is very slow
**Possible causes**:
- Cold start (first request is slower)
- Wrong region (try us-east-1)
- Network latency

**Fix**: Wait for first response, subsequent ones should be faster

## Verification Checklist

- [ ] AWS credentials configured (`aws sts get-caller-identity`)
- [ ] Bedrock model access granted (AWS Console → Bedrock → Model access)
- [ ] OpenAI provider still works (backward compatibility)
- [ ] Bedrock provider works (new feature)
- [ ] Can switch between providers seamlessly
- [ ] All query types work with Bedrock
- [ ] Internal tools work (feasibility restoration, sensitivity analysis)

## Files Changed Summary

### Created Files (3):
1. **llm_client.py** - LLM abstraction layer (450 lines)
2. **AWS_BEDROCK_GUIDE.md** - Comprehensive documentation
3. **BEDROCK_IMPLEMENTATION.md** - Implementation summary
4. **.env.example** - Environment variable template
5. **QUICKSTART.md** - This file

### Modified Files (5):
1. **requirements.txt** - Added boto3>=1.35.0
2. **app.py** - Added provider/model selection UI
3. **agents.py** - Added UnifiedLLMClient type support
4. **utils.py** - Added UnifiedLLMClient import
5. **README.md** - Updated installation and tutorial sections

## Cost Estimation (AWS Bedrock)

Approximate costs for testing:

| Model | Estimated Cost |
|-------|----------------|
| GPT-OSS-120B | High-capacity model |
| GPT-OSS-20B | More economical |
| Claude Sonnet 4 | Premium pricing |

**For typical OptiChat usage:**
- 1 model upload + 10 queries ≈ 50K tokens
- Cost varies by model selection

Set up AWS billing alerts to monitor costs!

## Next Steps After Testing

1. **Choose Your Default Provider**
   - Edit app.py line ~52 to change default from "openai" to "bedrock"

2. **Optimize Model Selection**
   - Use GPT-OSS-20B for simple queries
   - Use GPT-OSS-120B or Claude Sonnet 4 for complex optimization problems

3. **Monitor Costs**
   - Set up AWS CloudWatch metrics
   - Create billing alarms in AWS Console

4. **Customize Models**
   - Modify `BedrockLLMClient.MODEL_ID_MAP` in llm_client.py to add more models
   - Explore other Bedrock models available in your region

5. **Deploy**
   - Consider running on AWS EC2 with IAM role for easier credentials
   - Use AWS Secrets Manager for API keys

## Support

- **AWS Bedrock Issues**: Check AWS_BEDROCK_GUIDE.md
- **Implementation Details**: Check BEDROCK_IMPLEMENTATION.md
- **General OptiChat Help**: Check README.md

## Success Criteria

✅ You've successfully completed the integration when:
1. Both OpenAI and Bedrock providers work
2. You can switch between providers without restarting
3. All OptiChat features work with both providers
4. Model selection updates dynamically based on provider

Congratulations! OptiChat now supports multiple LLM providers! 🎉
