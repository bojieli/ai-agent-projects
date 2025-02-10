# Live Voice Chat Demo

A real-time voice chat demo featuring speech-to-text, AI conversation, and text-to-speech capabilities. The application supports multiple languages and provides a seamless conversational experience with minimal latency.

## Features

- 🎤 Real-time voice input with Voice Activity Detection (VAD)
- 🤖 AI-powered conversations using LLaMA model
- 🔊 Text-to-speech synthesis
- ⚡ Low-latency audio streaming
- 📊 Real-time latency monitoring and logging
- 🎯 WebSocket-based communication

## Prerequisites

- Node.js
- npm or yarn
- Modern web browser with WebAudio API support

## Project Structure

```
/backend
- server.js: Main WebSocket server handling audio streaming and AI interactions
- config.js: Configuration settings for APIs and server parameters
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
2. Install backend dependencies: `cd backend && npm install`
3. Install frontend dependencies: `cd frontend && npm install`
5. Configure API keys in backend/config.js

## Usage

1. Start the backend server: `cd backend && npm start`
2. Start the frontend development server: `cd frontend && npm run dev`
3. Open http://localhost:3001 in your browser
4. Click "Start Recording" to begin a conversation

## License

MIT

