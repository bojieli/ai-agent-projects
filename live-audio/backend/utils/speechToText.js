const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');
const path = require('path');
const config = require('../config');

class SpeechToTextService {
  constructor() {
    this.tempDir = path.join(__dirname, '../temp');
    this.ensureTempDirectory();
  }

  /**
   * Ensure temp directory exists
   */
  ensureTempDirectory() {
    if (!fs.existsSync(this.tempDir)) {
      fs.mkdirSync(this.tempDir, { recursive: true });
    }
  }

  /**
   * Convert raw audio buffer to WAV format
   * @param {Buffer} audioBuffer - Raw PCM audio data
   * @param {Object} options - Audio format options
   * @returns {Buffer} WAV formatted audio data
   */
  createWavBuffer(audioBuffer, options = {}) {
    const sampleRate = options.sampleRate || config.AUDIO_SAMPLE_RATE;
    const channels = options.channels || 1;
    const bitsPerSample = options.bitsPerSample || 16;
    
    const byteRate = sampleRate * channels * bitsPerSample / 8;
    const blockAlign = channels * bitsPerSample / 8;
    const dataSize = audioBuffer.length;
    const fileSize = 36 + dataSize;
    
    const header = Buffer.alloc(44);
    
    // RIFF header
    header.write('RIFF', 0);
    header.writeUInt32LE(fileSize, 4);
    header.write('WAVE', 8);
    
    // fmt chunk
    header.write('fmt ', 12);
    header.writeUInt32LE(16, 16); // PCM format chunk size
    header.writeUInt16LE(1, 20);  // PCM format
    header.writeUInt16LE(channels, 22);
    header.writeUInt32LE(sampleRate, 24);
    header.writeUInt32LE(byteRate, 28);
    header.writeUInt16LE(blockAlign, 32);
    header.writeUInt16LE(bitsPerSample, 34);
    
    // data chunk
    header.write('data', 36);
    header.writeUInt32LE(dataSize, 40);
    
    return Buffer.concat([header, audioBuffer]);
  }

  /**
   * Transcribe audio using OpenAI Whisper API through OpenRouter
   * @param {Buffer} audioBuffer - Raw audio data
   * @param {Object} options - Transcription options
   * @returns {Promise<Object>} Transcription result
   */
  async transcribeAudio(audioBuffer, options = {}) {
    try {
      // Create WAV buffer
      const wavBuffer = this.createWavBuffer(audioBuffer, {
        sampleRate: config.AUDIO_SAMPLE_RATE,
        channels: 1,
        bitsPerSample: 16
      });

      // Create temporary file
      const tempFileName = `audio_${Date.now()}_${Math.random().toString(36).substring(2)}.wav`;
      const tempFilePath = path.join(this.tempDir, tempFileName);
      
      // Write audio to temporary file
      fs.writeFileSync(tempFilePath, wavBuffer);

      try {
        // Create form data
        const formData = new FormData();
        formData.append('file', fs.createReadStream(tempFilePath));
        formData.append('model', config.STT_MODEL);
        formData.append('response_format', 'json');
        
        if (options.language) {
          formData.append('language', options.language);
        }
        
        if (options.prompt) {
          formData.append('prompt', options.prompt);
        }

        // Make API request
        const response = await axios({
          method: 'post',
          url: config.STT_API_URL,
          data: formData,
          headers: {
            'Authorization': `Bearer ${config.OPENAI_API_KEY}`,
            ...formData.getHeaders()
          },
          timeout: 30000 // 30 second timeout
        });

        const result = {
          success: true,
          text: response.data.text || '',
          language: response.data.language || 'unknown',
          duration: response.data.duration || 0,
          confidence: response.data.confidence || 1.0,
          timestamp: Date.now()
        };

        console.log('STT Result:', {
          text: result.text,
          language: result.language,
          duration: result.duration
        });

        return result;

      } finally {
        // Clean up temporary file
        try {
          fs.unlinkSync(tempFilePath);
        } catch (cleanupError) {
          console.warn('Failed to cleanup temp file:', cleanupError.message);
        }
      }

    } catch (error) {
      console.error('Speech-to-text error:', error.response?.data || error.message);
      
      return {
        success: false,
        text: '',
        error: error.response?.data?.error?.message || error.message,
        timestamp: Date.now()
      };
    }
  }

  /**
   * Clean up old temporary files
   */
  cleanupTempFiles() {
    try {
      const files = fs.readdirSync(this.tempDir);
      const now = Date.now();
      const maxAge = 10 * 60 * 1000; // 10 minutes
      
      files.forEach(file => {
        const filePath = path.join(this.tempDir, file);
        const stats = fs.statSync(filePath);
        
        if (now - stats.mtime.getTime() > maxAge) {
          try {
            fs.unlinkSync(filePath);
            console.log('Cleaned up old temp file:', file);
          } catch (error) {
            console.warn('Failed to cleanup old temp file:', file, error.message);
          }
        }
      });
    } catch (error) {
      console.warn('Failed to cleanup temp directory:', error.message);
    }
  }

  /**
   * Check if audio buffer has sufficient content for transcription
   * @param {Buffer} audioBuffer - Audio buffer to check
   * @returns {boolean} True if buffer has sufficient content
   */
  hasSufficientAudio(audioBuffer) {
    if (!audioBuffer || audioBuffer.length === 0) {
      return false;
    }

    // Check minimum duration (at least 0.1 seconds of audio)
    const minSamples = config.AUDIO_SAMPLE_RATE * 0.1; // 0.1 seconds
    const minBytes = minSamples * 2; // 16-bit = 2 bytes per sample
    
    if (audioBuffer.length < minBytes) {
      return false;
    }

    // Since we're using Silero VAD for speech detection, we trust its decision
    // and only check for minimum duration. The energy check is redundant and
    // can reject valid speech that Silero VAD correctly identified.
    return true;
  }
}

module.exports = SpeechToTextService; 