# Live Voice Chat Demo

A real-time voice chat demo featuring speech-to-text, AI conversation, and text-to-speech capabilities. The application supports multiple languages and provides a seamless conversational experience with minimal latency.

## Features

- 🎤 Real-time voice input with Voice Activity Detection (VAD)
- 🤖 AI-powered conversations using LLaMA model
- 🔊 Text-to-speech synthesis
- ⚡ Low-latency audio streaming
- 📊 Real-time latency monitoring and logging
- 🎯 WebSocket-based communication

## Architecture Overview

The system consists of a frontend-backend architecture with real-time audio processing:

### Frontend (Next.js)
- **Audio Capture**: Uses Web Audio API to capture microphone input
- **Audio Processing**: Client-side audio processing and streaming to backend
- **WebSocket Communication**: Sends audio stream to backend and receives responses
- **Audio Playback**: Plays back TTS audio responses from the backend

### Backend (Node.js)
- **WebSocket Server**: Handles real-time audio streaming and client connections
- **Voice Activity Detection**: Server-side Silero VAD processing to detect speech boundaries with high accuracy
- **Speech-to-Text**: Converts audio to text using OpenAI Whisper API
- **LLM Processing**: Processes user input using OpenAI LLMs
- **Text-to-Speech**: Converts AI responses to audio using SiliconFlow TTS API (Fish Audio TTS)

### Data Flow
```
User Speech → WebSocket → Backend VAD → STT → LLM → TTS → Audio Response
```

## Prerequisites

- Node.js (v16 or higher)
- npm or yarn
- Modern web browser with WebAudio API support
- OpenAI API key
- SiliconFlow API key (for TTS)

## Project Structure

```
/backend
- server.js: Main WebSocket server handling audio streaming and AI interactions
- config.js: Configuration settings for APIs and server parameters
- utils/vad.js: Voice Activity Detection implementation
- package.json: Backend dependencies and scripts
```

```
/frontend
- pages/: Next.js pages
  - index.tsx: Main application interface
- components/: Reusable UI components
- public/: Static assets
  - audioWorklet.js: Audio processing and VAD implementation
- next.config.js: Next.js configuration
- tailwind.config.js: Tailwind CSS settings
- package.json: Frontend dependencies and scripts
```

## Installation

1. Clone the repository
2. Install backend dependencies: 
   ```bash
   cd backend && npm install
   ```
3. Install frontend dependencies: 
   ```bash
   cd frontend && npm install
   ```
4. Download the Silero VAD model:
   ```bash
   cd backend/models
   wget https://huggingface.co/deepghs/silero-vad-onnx/resolve/main/silero_vad.onnx
   ```

## Configuration

### API Keys Setup

1. Copy the example configuration file:
   ```bash
   cp backend/config.js.example backend/config.js
   ```

2. Edit `backend/config.js` and add your API keys:
   ```javascript
   const config = {
     // OpenAI API Configuration
     OPENAI_API_KEY: 'your-openai-api-key-here',
     
     // SiliconFlow API Configuration (for TTS)
     SILICONFLOW_API_KEY: 'your-siliconflow-api-key-here',
     
     // ... other configuration options
   };
   ```

3. Required API keys:
   - **OpenAI API Key**: Required for Speech-to-Text (Whisper) and LLM (GPT) services
   - **SiliconFlow API Key**: Required for Text-to-Speech functionality

### Configuration Options

The `config.js` file contains various settings you can customize:

- **LLM Settings**: Model selection, API URLs, token limits
- **Silero VAD Settings**: Threshold, frame length, speech duration parameters
- **Audio Settings**: Sample rate, chunk size, quality parameters
- **Server Settings**: Port, host, system prompt

## Usage

1. Start the backend server: 
   ```bash
   cd backend && npm start
   ```
2. Start the frontend development server: 
   ```bash
   cd frontend && npm run dev
   ```
3. Open http://localhost:3000 in your browser
4. Click "Start Recording" to begin a conversation

## License

MIT

