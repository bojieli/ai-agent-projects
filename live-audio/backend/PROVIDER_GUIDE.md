# Provider Selection Guide for Live Audio Backend

This guide explains how to configure and use different AI service providers for ASR (Automatic Speech Recognition), LLM (Large Language Model), and TTS (Text-to-Speech) in the live audio backend.

## Overview

The backend now supports multiple providers for each service type:

- **ASR**: OpenAI Whisper, SenseVoice (via Siliconflow)
- **LLM**: OpenAI GPT-4o, OpenRouter GPT-4o, OpenRouter Gemini, ARK Doubao
- **TTS**: Fish Audio (via Siliconflow) - unchanged

## Configuration

### 1. Environment Variables

Set up your API keys as environment variables:

```bash
export OPENAI_API_KEY="your-openai-api-key"
export OPENROUTER_API_KEY="your-openrouter-api-key"
export ANTHROPIC_API_KEY="your-anthropic-api-key"  # For future use
export ARK_API_KEY="your-ark-api-key"
export SILICONFLOW_API_KEY="your-siliconflow-api-key"
```

### 2. Provider Selection

In your `config.js`, set the desired providers:

```javascript
const config = {
  // Provider Selection
  ASR_PROVIDER: 'openai',        // 'openai' or 'siliconflow'
  LLM_PROVIDER: 'openai',        // 'openai', 'openrouter-gpt4o', 'openrouter-gemini', 'ark'
  TTS_PROVIDER: 'siliconflow',   // 'siliconflow' (keep current)
  
  // ... rest of config
};
```

## Supported Providers

### ASR Providers

#### 1. OpenAI Whisper (`openai`)
- **Model**: `whisper-1`
- **API**: OpenAI Audio API
- **Strengths**: Excellent accuracy, good language support
- **Requirements**: `OPENAI_API_KEY`

#### 2. SenseVoice (`siliconflow`)
- **Model**: `FunAudioLLM/SenseVoiceSmall`
- **API**: Siliconflow Audio API
- **Strengths**: Low latency, cost-effective, auto language detection
- **Requirements**: `SILICONFLOW_API_KEY`

### LLM Providers

#### 1. OpenAI GPT-4o (`openai`)
- **Model**: `gpt-4o`
- **API**: OpenAI Chat Completions API
- **Strengths**: Excellent reasoning, balanced performance
- **Requirements**: `OPENAI_API_KEY`

#### 2. OpenRouter GPT-4o (`openrouter-gpt4o`)
- **Model**: `openai/gpt-4o`
- **API**: OpenRouter API
- **Strengths**: No geographic restrictions, unified interface
- **Requirements**: `OPENROUTER_API_KEY`

#### 3. OpenRouter Gemini (`openrouter-gemini`)
- **Model**: `google/gemini-2.5-flash`
- **API**: OpenRouter API
- **Strengths**: Fast response, good for real-time chat
- **Requirements**: `OPENROUTER_API_KEY`

#### 4. ARK Doubao (`ark`)
- **Model**: `doubao-seed-1-6-flash-250615`
- **API**: Volcengine ARK API
- **Strengths**: Low latency in China, optimized for Chinese
- **Requirements**: `ARK_API_KEY`

## Usage Examples

### Basic Configuration

```javascript
// config.js
const config = {
  ASR_PROVIDER: 'siliconflow',      // Use SenseVoice for ASR
  LLM_PROVIDER: 'openrouter-gemini', // Use Gemini via OpenRouter
  TTS_PROVIDER: 'siliconflow',       // Keep using Fish Audio
  
  // API keys loaded from environment
  OPENROUTER_API_KEY: process.env.OPENROUTER_API_KEY,
  SILICONFLOW_API_KEY: process.env.SILICONFLOW_API_KEY,
  // ... other config
};
```

### Dynamic Provider Switching

```javascript
// In your application code
const { ConnectionHandler } = require('./server');

// Switch ASR provider at runtime
connectionHandler.sttService.switchProvider('openai');

// Switch LLM provider at runtime
connectionHandler.switchLLMProvider('ark');
```

## Recommended Combinations

### For Real-time Performance
```javascript
ASR_PROVIDER: 'siliconflow',      // Fast SenseVoice
LLM_PROVIDER: 'openrouter-gemini', // Fast Gemini
TTS_PROVIDER: 'siliconflow'        // Fast Fish Audio
```

### For Best Accuracy
```javascript
ASR_PROVIDER: 'openai',           // Accurate Whisper
LLM_PROVIDER: 'openai',           // High-quality GPT-4o
TTS_PROVIDER: 'siliconflow'       // Natural Fish Audio
```

### For China Deployment
```javascript
ASR_PROVIDER: 'siliconflow',      // No geographic restrictions
LLM_PROVIDER: 'ark',              // Local Doubao service
TTS_PROVIDER: 'siliconflow'       // Local Siliconflow
```

### For Cost Optimization
```javascript
ASR_PROVIDER: 'siliconflow',      // Cost-effective SenseVoice
LLM_PROVIDER: 'openrouter-gemini', // Affordable Gemini
TTS_PROVIDER: 'siliconflow'       // Affordable Fish Audio
```

## Testing

### Running Tests

The backend includes comprehensive tests for all provider combinations:

```bash
# Install test dependencies
npm install

# Run all provider tests
npm run test:providers

# Or use the test runner
node run-tests.js
```

### Test Coverage

The test suite covers:
- ✅ Provider creation and configuration
- ✅ ASR transcription with real audio
- ✅ LLM chat completion and streaming
- ✅ All ASR+LLM provider combinations
- ✅ Dynamic provider switching
- ✅ Error handling and fallback

### Example Test Output

```
🧪 Starting Provider Tests for Live Audio Backend
============================================================

🔑 API Key Status:
  ✅ OpenRouter API key
  ✅ ARK (Doubao) API key
  ✅ Siliconflow API key
  ✅ OpenAI API key (optional)

📋 Test Plan:
  1. ASR Provider Tests (OpenAI Whisper, SenseVoice)
  2. LLM Provider Tests (OpenAI, OpenRouter GPT-4o, OpenRouter Gemini, ARK Doubao)
  3. Integration Tests (All ASR+LLM combinations)
  4. Provider Switching Tests

🚀 Running Tests...

  ASR Provider Tests
    openai ASR Provider
      ✓ should be created successfully
      ✓ should transcribe test audio (2.1s)
    siliconflow ASR Provider
      ✓ should be created successfully
      ✓ should transcribe test audio (1.8s)

  LLM Provider Tests
    openai LLM Provider
      ✓ should be created successfully
      ✓ should generate chat completion (3.2s)
      ✓ should stream chat completion (2.9s)
    openrouter-gpt4o LLM Provider
      ✓ should be created successfully
      ✓ should generate chat completion (2.8s)
      ✓ should stream chat completion (2.5s)

  Provider Integration Tests
    ✓ should work with OpenAI ASR + OpenAI LLM (5.3s)
    ✓ should work with OpenAI ASR + OpenRouter GPT-4o (4.9s)
    ✓ should work with SenseVoice ASR + ARK Doubao (4.1s)
    ...

============================================================
✅ All tests completed successfully!
```

## Troubleshooting

### Common Issues

1. **API Key Not Found**
   ```
   Error: API key OPENROUTER_API_KEY not found in configuration
   ```
   **Solution**: Ensure environment variable is set correctly

2. **Provider Creation Failed**
   ```
   Error: ASR provider openai not found in configuration
   ```
   **Solution**: Check provider name in config matches supported options

3. **Network Errors**
   ```
   Error: connect ECONNREFUSED
   ```
   **Solution**: Check network connectivity and API endpoint URLs

4. **Rate Limiting**
   ```
   Error: 429 Too Many Requests
   ```
   **Solution**: Implement retry logic or switch to different provider

### Performance Optimization

1. **For Low Latency**: Use `siliconflow` ASR + `openrouter-gemini` LLM
2. **For High Accuracy**: Use `openai` ASR + `openai` LLM
3. **For China**: Use `siliconflow` ASR + `ark` LLM
4. **For Cost**: Use `siliconflow` for all services

### Monitoring

Monitor provider performance using the built-in logging:

```javascript
// Enable detailed logging
console.log('ASR Provider Info:', sttService.getProviderInfo());
console.log('LLM Provider Info:', connectionHandler.llmProvider.config);
```

## Migration from Legacy Config

If upgrading from the old hardcoded configuration:

### Before (Legacy)
```javascript
const config = {
  OPENAI_API_KEY: 'your-key',
  LLM_API_URL: 'https://api.openai.com/v1/chat/completions',
  STT_API_URL: 'https://api.openai.com/v1/audio/transcriptions',
  // ...
};
```

### After (Provider Selection)
```javascript
const config = {
  // API Keys
  OPENAI_API_KEY: process.env.OPENAI_API_KEY,
  SILICONFLOW_API_KEY: process.env.SILICONFLOW_API_KEY,
  
  // Provider Selection
  ASR_PROVIDER: 'openai',
  LLM_PROVIDER: 'openai',
  TTS_PROVIDER: 'siliconflow',
  
  // Provider Configurations (auto-configured)
  ASR_PROVIDERS: { /* ... */ },
  LLM_PROVIDERS: { /* ... */ },
  // ...
};
```

The legacy configuration is still supported for backward compatibility, but using the new provider selection is recommended for better flexibility and maintainability.

## Reference

For more information about the specific AI models and APIs, see:
- [OpenRouter API Documentation](https://openrouter.ai/docs)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Siliconflow API Documentation](https://siliconflow.cn/docs)
- [ARK API Documentation](https://www.volcengine.com/docs/82379)

For the original guide and model selection strategies, see:
[OpenRouter、Anthropic、火山引擎、Siliconflow 使用指南](https://01.me/2025/07/llm-api-setup/) 