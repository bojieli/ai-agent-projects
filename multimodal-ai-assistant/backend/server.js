const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const axios = require('axios');
const config = require('./config');
const { preprocessSentence } = require('./utils/textProcessor');
const fs = require('fs');
const path = require('path');
const ffmpeg = require('fluent-ffmpeg');

// Import franc dynamically at the top level
let franc;
(async () => {
  const francModule = await import('franc');
  franc = francModule.franc;
})();

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

// Create a connection handler class to manage state for each connection
class ConnectionHandler {
  constructor(ws) {
    this.ws = ws;
    this.messageHistory = [];
    this.asrWs = null;
    this.currentLLMRequest = null;
    this.latestImage = null;
    this.currentTTSRequest = null;
    this.isASRConnected = false;
    this.lastProcessedTranscript = null;
    this.playbackStartTime = null;
    this.lastUserMessageId = null;
    this.currentMessageId = null;  // Track current message ID
    this.llmOrTTSIsWorking = false;
    this.ttsQueue = [];  // Queue for pending TTS requests
    this.isTTSProcessing = false;  // Flag to track if TTS is currently processing
    this.lastAudioEndTime = null;  // Track when the last audio chunk will finish playing
    this.audioTotalDuration = 0;   // Track total duration of queued audio

    // Add properties for audio recording
    this.audioChunks = [];
    this.isRecording = false;
    this.recordingStartTime = null;
    this.recordingPath = path.join(__dirname, 'recordings');
    
    // Create recordings directory if it doesn't exist
    if (!fs.existsSync(this.recordingPath)) {
      fs.mkdirSync(this.recordingPath, { recursive: true });
    }

    this.audioFormat = null;  // Add this property

    this.expectedPlaybackEndTime = null;  // Add this property

    this.lastSyncedHistoryLength = 0;  // Track how much of history has been synced
    this.lastSyncedHistory = [];  // Keep track of last synced state

    this.setupWebSocketHandlers();
    this.connectToASR();
  }

  setupWebSocketHandlers() {
    this.ws.on('message', this.handleMessage.bind(this));
    this.ws.on('close', this.handleClose.bind(this));
    this.ws.on('error', this.handleError.bind(this));
  }

  async handleMessage(message) {
    try {
      // Try to parse as JSON first
      const jsonMessage = JSON.parse(message);
      
      // Handle ping message by sending back pong with same timestamp
      if (jsonMessage.type === 'ping') {
        this.ws.send(JSON.stringify({
          type: 'pong',
          timestamp: jsonMessage.timestamp
        }));
        return;
      }

      // Handle image message
      if (jsonMessage.type === 'image') {
        this.latestImage = jsonMessage.data;
        console.log('Received new image from camera');
        return;
      }

      // Handle other ping message by sending back pong with same timestamp
      if (jsonMessage.type === 'ping') {
        this.ws.send(JSON.stringify({
          type: 'pong',
          timestamp: jsonMessage.timestamp
        }));
        return;
      }

      console.log('Received JSON message:', jsonMessage);
    } catch (e) {
      // If not JSON, treat as binary data
      if (Buffer.isBuffer(message)) {
        // Start recording if not already started
        if (!this.isRecording) {
          this.startRecording();
        }
        
        // Store the audio chunk
        this.audioChunks.push(message);

        // Forward audio data to ASR service
        if (this.asrWs && this.isASRConnected && this.asrWs.readyState === WebSocket.OPEN) {
          this.asrWs.send(message);
        } else {
          console.log('ASR WebSocket not ready, buffering or dropping audio data');
        }
      } else {
        console.error('Received unexpected data type:', typeof message);
      }
    }
  }

  handleClose() {
    console.log('Client disconnected');
    this.cleanup();
  }

  handleError(error) {
    console.error('WebSocket error:', error);
    this.cleanup();
  }

  cleanup() {
    if (this.asrWs && this.isASRConnected) {
      try {
        this.asrWs.close();
      } catch (error) {
        console.error('Error closing ASR WebSocket:', error);
      }
    }
    if (this.currentLLMRequest) {
      this.currentLLMRequest.cancel();
    }
    if (this.currentTTSRequest) {
      this.currentTTSRequest.cancel();
    }
    this.ttsQueue = [];
    this.lastAudioEndTime = null;
    this.audioTotalDuration = 0;

    // Save any remaining recording
    if (this.isRecording) {
      this.isRecording = false;
      this.saveRecording();
      this.audioChunks = [];
    }
  }

  logEvent(type, details = {}) {
    const timestamp = new Date().toISOString();
    console.log(`[${timestamp}] Event: ${type}`, {
      ...details,
      connectionId: this.ws._socket.remoteAddress
    });
  }

  // Add helper method to generate message IDs
  generateMessageId() {
    return Math.random().toString(36).substring(2, 15);
  }

  async handleASRMessage(asrMessage) {
    const result = JSON.parse(asrMessage);

    if (result.type === 'transcript') {
      const { transcript, is_final } = result;
      
      // Generate new message ID for final transcripts
      if (is_final) {
        this.currentMessageId = this.generateMessageId();
      }

      // Include message ID in transcript events
      this.ws.send(JSON.stringify({ 
        type: 'transcript', 
        text: transcript, 
        isFinal: is_final,
        messageId: this.currentMessageId
      }));
      
      this.logEvent('transcript', { text: transcript, isFinal: is_final, messageId: this.currentMessageId });

      // Concatenate final transcript if available
      const fullTranscript = this.finalTranscript ? this.finalTranscript + ' ' + transcript : transcript;
      if (is_final) {
        this.finalTranscript = fullTranscript;
      }

      // Only process if this transcript is different from the last one we processed
      if (!is_final || fullTranscript !== this.lastProcessedTranscript) {
        this.lastProcessedTranscript = fullTranscript;
        
        // Update message history similar to frontend
        const lastMessage = this.messageHistory[this.messageHistory.length - 1];
        const isLastMessageUser = lastMessage && 
          (lastMessage.role === 'user' || lastMessage.role === 'transcript');

        if (isLastMessageUser) {
          // Replace the last user message
          this.messageHistory = [
            ...this.messageHistory.slice(0, -1),
            { role: 'user', content: fullTranscript, messageId: this.currentMessageId }
          ];
        } else {
          // Append new message
          this.messageHistory.push({ 
            role: 'user', 
            content: fullTranscript,
            messageId: this.currentMessageId 
          });
        }

        this.syncChatHistory();
        this.generateAIResponse();
      }
    } else if (result.type === 'speech_start') {
      // Clear the TTS queue when speech starts
      this.ttsQueue = [];
      this.lastAudioEndTime = null;
      this.audioTotalDuration = 0;
      
      // Include current message ID in speech_start event
      this.ws.send(JSON.stringify({ 
        type: 'speech_start',
        messageId: this.currentMessageId
      }));

      // Handle interrupt if LLM or TTS is working
      if (this.llmOrTTSIsWorking) {
        const now = Date.now();
        const elapsedPlaybackTime = this.playbackStartTime 
          ? now - this.playbackStartTime 
          : 0;
        const isPlaybackFinished = this.expectedPlaybackEndTime 
          ? now >= this.expectedPlaybackEndTime 
          : false;

        // Send debug info to frontend
        console.log('Interrupt due to speech start: elapsedPlaybackTime:', elapsedPlaybackTime, 'isPlaybackFinished:', isPlaybackFinished);
        this.ws.send(JSON.stringify({
          type: 'debug_info',
          message: `Interrupt due to speech start - Playback Finished: ${isPlaybackFinished}, Playback time: ${elapsedPlaybackTime}ms`
        }));

        // Cancel ongoing operations
        if (this.currentLLMRequest) {
          this.currentLLMRequest.cancel();
        }
        if (this.currentTTSRequest) {
          this.currentTTSRequest.cancel();
        }

        // Reset state based on playback time and expected end time
        if (!this.playbackStartTime || 
            (elapsedPlaybackTime <= config.CANCEL_PLAYBACK_TIME_THRESHOLD && !isPlaybackFinished)) {
          const lastAssistantIndex = this.messageHistory.map(msg => msg.role).lastIndexOf('assistant');
          if (lastAssistantIndex !== -1) {
            console.log('Removing most recent assistant message from history');
            this.messageHistory = [
              ...this.messageHistory.slice(0, lastAssistantIndex),
              ...this.messageHistory.slice(lastAssistantIndex + 1)
            ];
            this.syncChatHistory();  // Sync after removing message
          }
        } else if (elapsedPlaybackTime > config.CANCEL_PLAYBACK_TIME_THRESHOLD || isPlaybackFinished) {
          // Reset final transcript if playback finished or was interrupted after threshold
          this.finalTranscript = '';
        }
      }

      // Reset playback tracking
      this.llmOrTTSIsWorking = false;
      this.playbackStartTime = null;
      this.expectedPlaybackEndTime = null;
      this.ttsQueue = [];
      this.lastAudioEndTime = null;
    } else if (result.type === 'speech_end') {
      // Save the recording when speech ends
      if (this.isRecording) {
        this.isRecording = false;
        this.saveRecording();
        this.audioChunks = [];
      }
      
      this.ws.send(JSON.stringify({ type: 'speech_end' }));
      this.logEvent('speech_end');
    }
  }

  async generateAIResponse() {
    this.llmOrTTSIsWorking = true;
    try {
      this.currentLLMRequest = axios.CancelToken.source();
      
      this.ws.send(JSON.stringify({ type: 'llm_start' }));
      this.logEvent('llm_start');

      let hasReceivedFirstToken = false;
      let hasReceivedFirstSentence = false;
      let currentSentence = '';
      let isFirstSentence = true;
      
      // Keep only the last 20 messages for context
      const recentHistory = this.messageHistory.slice(-20);
      let messages = [
        { role: 'system', content: config.SYSTEM_PROMPT },
        ...recentHistory.map(({ role, content }) => ({ role, content }))
      ];

      // If we have a latest image, include it in the messages
      if (this.latestImage) {
        // Find the last user message
        const lastUserMessageIndex = messages.findIndex(msg => msg.role === 'user');
        if (lastUserMessageIndex !== -1) {
          // Add image to the user's message
          messages[lastUserMessageIndex] = {
            role: 'user',
            content: [
              {
                type: 'image_url',
                image_url: {
                  url: this.latestImage,
                  detail: 'low'
                }
              },
              {
                type: 'text',
                text: messages[lastUserMessageIndex].content
              }
            ]
          };
        }
        // Clear the image after using it
        this.latestImage = null;
      }

      // Add initial empty assistant message
      this.messageHistory.push({
        role: 'assistant',
        content: '',
        messageId: this.currentMessageId
      });
      this.syncChatHistory();

      let accumulatedContent = '';  // Track all content received so far

      const response = await axios.post(
        config.LLM_API_URL,
        {
          model: config.LLM_MODEL,
          messages: messages,
          stream: true,
          max_tokens: config.VISION_MAX_TOKENS
        },
        {
          headers: {
            'Authorization': `Bearer ${config.OPENAI_API_KEY}`,
            'Content-Type': 'application/json',
          },
          cancelToken: this.currentLLMRequest.token,
          responseType: 'stream'
        }
      );

      let buffer = ''; // Add this buffer to store incomplete lines

      response.data.on('data', async chunk => {
        try {
          buffer += chunk.toString();
          const lines = buffer.split('\n');
          // Keep the last line if it's incomplete
          buffer = lines.pop() || '';

          for (const line of lines) {
            const trimmedLine = line.trim();
            if (!trimmedLine || trimmedLine === '[DONE]') continue;
            if (!trimmedLine.startsWith('data: ')) continue;

            try {
              const jsonData = JSON.parse(trimmedLine.replace('data: ', ''));
              const content = jsonData.choices[0]?.delta?.content || '';
              if (!content) continue;

              if (!hasReceivedFirstToken) {
                hasReceivedFirstToken = true;
                this.ws.send(JSON.stringify({ 
                  type: 'llm_first_token',
                  messageId: this.currentMessageId
                }));
              }

              currentSentence += content;
              accumulatedContent += content;

              if (this.isCompleteSentence(currentSentence, isFirstSentence)) {
                // Update message history with accumulated content after each complete sentence
                const lastMessage = this.messageHistory[this.messageHistory.length - 1];
                lastMessage.content = accumulatedContent;
                this.syncChatHistory();

                const completedSentence = currentSentence;
                currentSentence = '';
                isFirstSentence = false;

                this.ws.send(JSON.stringify({ 
                  type: 'llm_sentence', 
                  text: completedSentence,
                  messageId: this.currentMessageId
                }));

                if (!hasReceivedFirstSentence) {
                  hasReceivedFirstSentence = true;
                  this.ws.send(JSON.stringify({ 
                    type: 'llm_first_sentence',
                    messageId: this.currentMessageId
                  }));
                }

                await this.synthesizeAndStreamAudio(completedSentence);
              }
            } catch (parseError) {
              console.error('Error parsing JSON data:', parseError);
              continue;
            }
          }
        } catch (error) {
          console.error('Error processing LLM stream:', error);
        }
      });

      // Handle any remaining data in the buffer when the stream ends
      response.data.on('end', async () => {
        try {
          if (buffer) {
            const trimmedLine = buffer.trim();
            if (trimmedLine && trimmedLine !== '[DONE]' && trimmedLine.startsWith('data: ')) {
              const jsonData = JSON.parse(trimmedLine.replace('data: ', ''));
              const content = jsonData.choices[0]?.delta?.content || '';
              if (content) {
                currentSentence += content;
                accumulatedContent += content;
              }
            }
          }

          // Handle any remaining content
          if (currentSentence.trim()) {
            await this.synthesizeAndStreamAudio(currentSentence);
            accumulatedContent += currentSentence;
            
            // Update message history with final content
            const lastMessage = this.messageHistory[this.messageHistory.length - 1];
            lastMessage.content = accumulatedContent;
            this.syncChatHistory();
          }

          this.ws.send(JSON.stringify({ 
            type: 'ai_response_complete',
            messageId: this.currentMessageId
          }));
        } catch (error) {
          console.error('Error processing final LLM data:', error);
        }
      });

    } catch (error) {
      this.llmOrTTSIsWorking = false;
      if (!axios.isCancel(error)) {
        console.error('Error generating AI response:', error);
        this.ws.send(JSON.stringify({ type: 'error', message: 'Error generating AI response' }));
        this.logEvent('error', { message: 'Error generating AI response', error: error.toString() });
      }
    }
  }

  isCompleteSentence(sentence, isFirstSentence) {
    const trimmedSentence = sentence.trim();

    // Check if we're inside a markdown code block
    if (trimmedSentence.includes('```')) {
      const count = (trimmedSentence.match(/```/g) || []).length;
      // If the count is odd, we're still inside a code block
      if (count % 2 !== 0) {
        return false;
      }
    }

    // Check if the sentence is a function call
    if (trimmedSentence.includes('<function>')) {
      return trimmedSentence.includes('</function>');
    }

    // Check for newline
    if (sentence.endsWith('\n')) {
      return true;
    }

    // Check for period, but not if it's a numbered list item
    if (trimmedSentence.endsWith('.')) {
      if (/[0-9]+\.$/.test(trimmedSentence)) {
        return false;
      }
      return true;
    }

    // Check for question mark or exclamation mark
    if (trimmedSentence.endsWith('?') || trimmedSentence.endsWith('!')) {
      return true;
    }

    // Check for Chinese punctuation
    if (trimmedSentence.endsWith('。') || trimmedSentence.endsWith('？') || trimmedSentence.endsWith('！')) {
      return true;
    }

    // Check for semicolons (both English and Chinese)
    if (trimmedSentence.endsWith(';') || trimmedSentence.endsWith('；')) {
      return true;
    }

    // Check if sentence ends with an emoji
    if (trimmedSentence.length > 0) {
      const lastChar = trimmedSentence.slice(-2); // Take last 2 chars for emoji
      const emojiRegex = /[\u{1F300}-\u{1F9FF}]|[\u{2600}-\u{26FF}]/u;
      if (emojiRegex.test(lastChar)) {
        return true;
      }
    }

    // First sentence should be as short as possible
    if (isFirstSentence) {
      if (trimmedSentence.endsWith(',') || trimmedSentence.endsWith('，')) {
        return true;
      }
    }

    return false;
  }

  async synthesizeAndStreamAudio(text) {
    try {
      // Skip empty or whitespace-only strings
      if (!text || !text.trim()) {
        console.log('Skipping TTS for empty string');
        return;
      }

      // Add text to the queue
      this.ttsQueue.push(text);
      
      // Try to process the queue
      await this.processTTSQueue();
    } catch (error) {
      if (!axios.isCancel(error)) {
        console.error('Error in TTS:', error);
        this.logEvent('error', { message: 'TTS error', error: error.toString() });
      }
      this.isTTSProcessing = false;
    }
  }

  // Helper method to calculate audio duration from WAV buffer
  calculateAudioDuration(audioBuffer) {
    if (audioBuffer.length < 44) return 0;
    
    const sampleRate = audioBuffer.readUInt32LE(24);
    const numChannels = audioBuffer.readUInt16LE(22);
    const bitsPerSample = audioBuffer.readUInt16LE(34);
    const dataSize = audioBuffer.length - 44; // Subtract WAV header size
    
    // Calculate duration in milliseconds
    const duration = Math.floor(
      (dataSize * 8 * 1000) / (sampleRate * numChannels * bitsPerSample)
    );
    
    return duration;
  }

  // Add method to start a new recording
  startRecording() {
    this.audioChunks = [];
    this.isRecording = true;
    this.recordingStartTime = new Date();
  }

  // Add method to save the recording
  saveRecording() {
    if (this.audioChunks.length === 0) return;

    const timestamp = this.recordingStartTime.toISOString().replace(/[:.]/g, '-');
    const fileName = `recording_${timestamp}.wav`;
    const filePath = path.join(this.recordingPath, fileName);

    // Create WAV header
    const dataSize = this.audioChunks.reduce((acc, chunk) => acc + chunk.length, 0);
    const header = Buffer.alloc(44);

    // RIFF chunk descriptor
    header.write('RIFF', 0);
    header.writeUInt32LE(36 + dataSize, 4);
    header.write('WAVE', 8);

    // fmt sub-chunk
    header.write('fmt ', 12);
    header.writeUInt32LE(16, 16); // Subchunk1Size
    header.writeUInt16LE(1, 20); // AudioFormat (PCM)
    header.writeUInt16LE(1, 22); // NumChannels (Mono)
    header.writeUInt32LE(16000, 24); // SampleRate
    header.writeUInt32LE(32000, 28); // ByteRate (SampleRate * NumChannels * BitsPerSample/8)
    header.writeUInt16LE(2, 32); // BlockAlign (NumChannels * BitsPerSample/8)
    header.writeUInt16LE(16, 34); // BitsPerSample

    // data sub-chunk
    header.write('data', 36);
    header.writeUInt32LE(dataSize, 40);

    // Write header and audio data to file
    const writeStream = fs.createWriteStream(filePath);
    writeStream.write(header);

    for (const chunk of this.audioChunks) {
      writeStream.write(chunk);
    }

    writeStream.end();
    this.logEvent('recording_saved', { filePath, size: dataSize + 44 });
  }

  async detectLanguage(text) {
    try {
      if (!franc) {
        const francModule = await import('franc');
        franc = francModule.franc;
      }

      const detectedLang = franc(text, { minLength: 1 });
      const langMap = {
        'cmn': 'zh',
        'eng': 'en',
        'jpn': 'jp',
        'zho': 'zh',
        'chi': 'zh',
        'und': 'en'
      };
      
      return langMap[detectedLang] || 'en';
    } catch (error) {
      console.error('Language detection error:', error);
      return 'en';
    }
  }

  connectToASR() {
    try {
      this.asrWs = new WebSocket(config.ASR_WEBSOCKET_URL);

      this.asrWs.on('open', () => {
        console.log('ASR WebSocket connected');
        this.isASRConnected = true;
      });

      this.asrWs.on('message', (msg) => this.handleASRMessage(msg));

      this.asrWs.on('close', () => {
        console.log('ASR WebSocket closed. Reconnecting...');
        this.isASRConnected = false;
        setTimeout(() => this.connectToASR(), 1000);
      });

      this.asrWs.on('error', (error) => {
        console.error('ASR WebSocket error:', error);
        this.isASRConnected = false;
      });
    } catch (error) {
      console.error('Error connecting to ASR:', error);
      setTimeout(() => this.connectToASR(), 1000);
    }
  }

  // Add this method to process TTS queue
  async processTTSQueue() {
    if (this.isTTSProcessing || this.ttsQueue.length === 0) return;

    this.isTTSProcessing = true;
    const now = Date.now();

    // Calculate remaining audio duration
    const remainingDuration = this.lastAudioEndTime 
      ? Math.max(0, this.lastAudioEndTime - now) 
      : 0;

    // Only process next TTS if remaining audio is less than 5 seconds
    if (remainingDuration <= 5000) {
      const text = this.ttsQueue[0];
      const ttsStartTime = Date.now();
      
      try {
        this.ws.send(JSON.stringify({ type: 'tts_start' }));
        this.logEvent('tts_start');
        
        const detectedLang = await this.detectLanguage(text);
        this.logEvent('language_detection', { text, detectedLang });
        
        const processedText = preprocessSentence(text, detectedLang);
        // Skip TTS if processed text is empty
        if (!processedText.trim()) {
          this.ttsQueue.shift(); // Remove empty text from queue
          this.isTTSProcessing = false;
          // Process next item in queue if any
          if (this.ttsQueue.length > 0) {
            setTimeout(() => this.processTTSQueue(), 100);
          }
          return;
        }

        this.currentTTSRequest = axios.CancelToken.source();
        const response = await axios({
          method: 'post',
          url: config.TTS_API_URL,
          data: {
            "model": "fishaudio/fish-speech-1.5",
            "input": text,
            "voice": "fishaudio/fish-speech-1.5:diana",
            "response_format": "mp3",
            "sample_rate": 32000,
            "stream": true,
            "speed": 1,
            "gain": 0
          },
          headers: {
            "Authorization": `Bearer ${config.SILICONFLOW_API_KEY}`,
            "Content-Type": "application/json"
          },
          responseType: 'stream',
          cancelToken: this.currentTTSRequest.token,
        });

        let headerBuffer = Buffer.alloc(0);
        let headerSent = false;
        let totalDataSize = 0;

        response.data.on('data', async chunk => {
          if (!headerSent) {
            headerBuffer = Buffer.concat([headerBuffer, chunk]);
            
            if (headerBuffer.length >= 44) {
              const sampleRate = headerBuffer.readUInt32LE(24);
              const numChannels = headerBuffer.readUInt16LE(22);
              const bitsPerSample = headerBuffer.readUInt16LE(34);

              this.audioFormat = { sampleRate, numChannels, bitsPerSample };

              const needsResampling = sampleRate !== 16000 || numChannels !== 1;

              if (needsResampling) {
                this.audioBuffer = Buffer.from(headerBuffer);
                headerBuffer = Buffer.alloc(0);
                headerSent = true;
                return;
              }

              const bytesPerSample = bitsPerSample / 8;
              const samplesPerSecond = sampleRate * numChannels;
              const bytesPerSecond = samplesPerSecond * bytesPerSample;
              const chunkSize = Math.floor(bytesPerSecond * 0.05); // 50ms worth of audio data

              this.ws.send(JSON.stringify({ 
                type: 'audio_start',
                format: {
                  sampleRate,
                  numChannels,
                  bitsPerSample
                }
              }));

              // Set playback start time immediately
              if (!this.playbackStartTime) {
                this.playbackStartTime = Date.now();
              }
              // Start sending audio data immediately (skip the header and data chunk header)
              if (headerBuffer.length > 44) {
                let remainingData = headerBuffer.slice(44);
                
                // Skip data chunk header (8 bytes) if present
                if (remainingData.length >= 8 && 
                    remainingData.slice(0, 4).toString() === 'data') {
                  remainingData = remainingData.slice(8);
                }

                while (remainingData.length >= chunkSize) {
                  const chunk = remainingData.slice(0, chunkSize);
                  this.ws.send(chunk);
                  totalDataSize += chunk.length;
                  remainingData = remainingData.slice(chunkSize);
                }
                headerBuffer = remainingData.length > 0 ? remainingData : Buffer.alloc(0);
              }

              headerSent = true;
            }
          } else {
            if (this.audioFormat.sampleRate !== 16000 || this.audioFormat.numChannels !== 1) {
              this.audioBuffer = Buffer.concat([this.audioBuffer, chunk]);
            } else {
              const bytesPerSample = this.audioFormat.bitsPerSample / 8;
              const samplesPerSecond = this.audioFormat.sampleRate * this.audioFormat.numChannels;
              const bytesPerSecond = samplesPerSecond * bytesPerSample;
              const chunkSize = Math.floor(bytesPerSecond * 0.05);

              let audioData = Buffer.concat([headerBuffer, chunk]);
              headerBuffer = Buffer.alloc(0);

              while (audioData.length >= chunkSize) {
                const chunkToSend = audioData.slice(0, chunkSize);
                this.ws.send(chunkToSend);
                totalDataSize += chunkSize;
                audioData = audioData.slice(chunkSize);
              }

              if (audioData.length > 0) {
                headerBuffer = audioData;
              }
            }
          }
        });

        response.data.on('end', async () => {
          try {
            if (this.audioFormat.sampleRate !== 16000 || this.audioFormat.numChannels !== 1) {
              // Create temporary files for resampling
              const inputPath = path.join(__dirname, `temp_input_${Date.now()}.wav`);
              const outputPath = path.join(__dirname, `temp_output_${Date.now()}.wav`);

              // Write the input audio buffer to a temporary file
              fs.writeFileSync(inputPath, this.audioBuffer);

              // Create a promise to handle the ffmpeg conversion
              await new Promise((resolve, reject) => {
                ffmpeg(inputPath)
                  .toFormat('wav')
                  .outputOptions([
                    '-acodec pcm_s16le',  // Set codec to 16-bit PCM
                    '-ar 16000',          // Set sample rate to 16kHz
                    '-ac 1'               // Set to mono channel
                  ])
                  .on('error', (err) => {
                    console.error('FFmpeg error:', err);
                    reject(err);
                  })
                  .on('end', () => resolve())
                  .save(outputPath);
              });

              // Read the resampled audio
              const resampledBuffer = fs.readFileSync(outputPath);

              // Clean up temporary files
              fs.unlinkSync(inputPath);
              fs.unlinkSync(outputPath);

              // Send audio start with resampled format
              this.ws.send(JSON.stringify({
                type: 'audio_start',
                format: {
                  sampleRate: 16000,
                  numChannels: 1,
                  bitsPerSample: 16
                }
              }));

              // Set playback start time
              if (!this.playbackStartTime) {
                this.playbackStartTime = Date.now();
              }

              // Find the data chunk in the resampled buffer
              let dataStart = 44; // Start looking after standard WAV header
              while (dataStart < resampledBuffer.length - 8) {
                if (resampledBuffer.readUInt32LE(dataStart) === 0x61746164) { // "data" chunk ID
                  dataStart += 8; // Skip "data" ID (4 bytes) and chunk size (4 bytes)
                  break;
                }
                dataStart++;
              }

              // Calculate chunk size for 50ms of audio at 16kHz mono
              const chunkSize = Math.floor(16000 * 2 * 0.05); // 16kHz * 16-bit * 50ms

              // Send audio data in chunks, starting after the data header
              let currentPos = dataStart;
              while (currentPos < resampledBuffer.length) {
                const end = Math.min(currentPos + chunkSize, resampledBuffer.length);
                const audioChunk = resampledBuffer.slice(currentPos, end);
                this.ws.send(audioChunk);
                totalDataSize += audioChunk.length;
                currentPos += chunkSize;
              }

            } else {
              // For non-resampled audio, process the remaining audio buffer
              const audioData = this.audioBuffer;
              if (audioData) {
                // Calculate chunk size for 50ms of audio
                const chunkSize = Math.floor(16000 * 2 * 0.05);

                // Send audio data in chunks
                let currentPos = dataStart;
                while (currentPos < audioData.length) {
                  const end = Math.min(currentPos + chunkSize, audioData.length);
                  const audioChunk = audioData.slice(currentPos, end);
                  this.ws.send(audioChunk);
                  totalDataSize += audioChunk.length;
                  currentPos += chunkSize;
                }
              }
            }

            const synthesisTime = Date.now() - ttsStartTime;
            this.ws.send(JSON.stringify({ 
              type: 'tts_complete',
              synthesisTime 
            }));
            this.ws.send(JSON.stringify({ type: 'audio_end' }));
            this.logEvent('tts_complete', { synthesisTime });

            // Calculate audio duration and update expected playback end time
            const audioDuration = Math.floor((totalDataSize * 8 * 1000) / (16000 * 1 * 16));
            this.expectedPlaybackEndTime = (this.expectedPlaybackEndTime || Date.now()) + audioDuration;
            this.lastAudioEndTime = Date.now() + audioDuration;
            
            // Remove the processed text from queue
            this.ttsQueue.shift();
            this.isTTSProcessing = false;
            
            // Process next item in queue if any
            if (this.ttsQueue.length > 0) {
              setTimeout(() => this.processTTSQueue(), 100);
            }
          } catch (error) {
            console.error('Error processing audio:', error);
            this.logEvent('error', { message: 'Audio processing error', error: error.toString() });
            
            // Clean up state
            this.ttsQueue.shift();
            this.isTTSProcessing = false;
          }
        });

        response.data.on('error', (error) => {
          console.error('Error in TTS stream:', error);
          this.logEvent('error', { message: 'TTS stream error', error: error.toString() });
          this.ttsQueue.shift();  // Remove failed text from queue
          this.isTTSProcessing = false;
        });

      } catch (error) {
        if (!axios.isCancel(error)) {
          console.error('Error in TTS:', error);
          this.logEvent('error', { message: 'TTS error', error: error.toString() });
        }
        this.ttsQueue.shift();  // Remove failed text from queue
        this.isTTSProcessing = false;
      }
    } else {
      this.isTTSProcessing = false;
      // Try again later if there's still too much audio in the queue
      setTimeout(() => this.processTTSQueue(), 100);
    }
  }

  // Update the syncChatHistory method to implement delta sync
  syncChatHistory() {
    const currentHistory = this.messageHistory;
    const lastHistory = this.lastSyncedHistory;
    
    // Find the index where histories start to differ
    let diffStartIndex = 0;
    while (diffStartIndex < lastHistory.length && 
           diffStartIndex < currentHistory.length && 
           JSON.stringify(lastHistory[diffStartIndex]) === JSON.stringify(currentHistory[diffStartIndex])) {
      diffStartIndex++;
    }

    // Get the new or modified messages
    const updatedMessages = currentHistory.slice(diffStartIndex);
    
    // Send delta update
    this.ws.send(JSON.stringify({
      type: 'chat_history_delta',
      startIndex: diffStartIndex,
      messages: updatedMessages
    }));

    // Update last synced state
    this.lastSyncedHistory = JSON.parse(JSON.stringify(currentHistory));
  }
}

// Handle new WebSocket connections
wss.on('connection', (ws) => {
  console.log('Client connected');
  new ConnectionHandler(ws);
});

server.listen(config.LISTEN_PORT, config.LISTEN_HOST, () => {
  console.log(`Server is running on ${config.LISTEN_HOST}:${config.LISTEN_PORT}`);
});
