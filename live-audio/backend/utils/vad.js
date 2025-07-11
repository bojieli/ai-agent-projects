const config = require('../config');

class VoiceActivityDetector {
  constructor(options = {}) {
    this.threshold = options.threshold || config.VAD_THRESHOLD;
    this.frameLength = options.frameLength || config.VAD_FRAME_LENGTH;
    this.minSpeechDuration = options.minSpeechDuration || config.VAD_MIN_SPEECH_DURATION;
    this.maxSilenceDuration = options.maxSilenceDuration || config.VAD_MAX_SILENCE_DURATION;
    this.sampleRate = options.sampleRate || config.AUDIO_SAMPLE_RATE;
    
    // State variables
    this.isSpeaking = false;
    this.speechStartTime = null;
    this.lastSpeechTime = null;
    this.audioBuffer = Buffer.alloc(0);
    this.speechBuffer = Buffer.alloc(0);
    
    // History for smoothing
    this.energyHistory = [];
    this.historySize = 5;
  }

  /**
   * Calculate energy of audio frame (matches frontend calculation)
   * @param {Buffer} audioData - Raw audio data (PCM 16-bit)
   * @returns {number} Energy value (normalized float)
   */
  calculateEnergy(audioData) {
    if (audioData.length === 0) return 0;
    
    let sum = 0;
    const sampleCount = audioData.length / 2;
    
    // Convert to normalized float and calculate energy like frontend
    for (let i = 0; i < audioData.length; i += 2) {
      if (i + 1 < audioData.length) {
        // Read 16-bit signed integer (little endian) and normalize to -1 to 1
        const sample = audioData.readInt16LE(i) / 32768;
        sum += sample * sample;
      }
    }
    
    // Return average energy (matches frontend: sum / samples.length)
    return sum / sampleCount;
  }

  /**
   * Apply smoothing to energy values
   * @param {number} energy - Current energy value
   * @returns {number} Smoothed energy value
   */
  smoothEnergy(energy) {
    this.energyHistory.push(energy);
    if (this.energyHistory.length > this.historySize) {
      this.energyHistory.shift();
    }
    
    // Calculate moving average
    const sum = this.energyHistory.reduce((a, b) => a + b, 0);
    return sum / this.energyHistory.length;
  }

  /**
   * Process audio chunk and detect voice activity
   * @param {Buffer} audioChunk - Raw audio data
   * @returns {Object} VAD result with detection status and audio data
   */
  processAudioChunk(audioChunk) {
    const currentTime = Date.now();
    
    // Add to buffer
    this.audioBuffer = Buffer.concat([this.audioBuffer, audioChunk]);
    
    // Process complete frames
    const results = [];
    const frameSize = this.frameLength * 2; // 16-bit = 2 bytes per sample
    
    while (this.audioBuffer.length >= frameSize) {
      const frame = this.audioBuffer.slice(0, frameSize);
      this.audioBuffer = this.audioBuffer.slice(frameSize);
      
      const energy = this.calculateEnergy(frame);
      const smoothedEnergy = this.smoothEnergy(energy);
      
      const isVoiceActive = smoothedEnergy > this.threshold;
      
      if (isVoiceActive) {
        if (!this.isSpeaking) {
          // Speech started
          this.isSpeaking = true;
          this.speechStartTime = currentTime;
          this.speechBuffer = Buffer.alloc(0);
        }
        
        this.lastSpeechTime = currentTime;
        this.speechBuffer = Buffer.concat([this.speechBuffer, frame]);
        
      } else if (this.isSpeaking) {
        // Check if silence duration exceeds threshold
        const silenceDuration = currentTime - this.lastSpeechTime;
        
        if (silenceDuration > this.maxSilenceDuration) {
          // Speech ended
          const speechDuration = currentTime - this.speechStartTime;
          
          if (speechDuration >= this.minSpeechDuration) {
            console.log('VAD: Speech ended', { 
              duration: speechDuration, 
              bufferSize: this.speechBuffer.length 
            });
            
            results.push({
              type: 'speech_end',
              audioData: this.speechBuffer,
              duration: speechDuration,
              timestamp: currentTime
            });
          }
          
          this.isSpeaking = false;
          this.speechStartTime = null;
          this.lastSpeechTime = null;
          this.speechBuffer = Buffer.alloc(0);
        } else {
          // Still in speech, add silence frame
          this.speechBuffer = Buffer.concat([this.speechBuffer, frame]);
        }
      }
    }
    
    return results;
  }

  /**
   * Force end current speech session
   * @returns {Object|null} Final speech data if available
   */
  forceEndSpeech() {
    if (this.isSpeaking && this.speechBuffer.length > 0) {
      const currentTime = Date.now();
      const speechDuration = currentTime - this.speechStartTime;
      
      if (speechDuration >= this.minSpeechDuration) {
        const result = {
          type: 'speech_end',
          audioData: this.speechBuffer,
          duration: speechDuration,
          timestamp: currentTime
        };
        
        this.isSpeaking = false;
        this.speechStartTime = null;
        this.lastSpeechTime = null;
        this.speechBuffer = Buffer.alloc(0);
        
        return result;
      }
    }
    
    this.reset();
    return null;
  }

  /**
   * Reset VAD state
   */
  reset() {
    this.isSpeaking = false;
    this.speechStartTime = null;
    this.lastSpeechTime = null;
    this.audioBuffer = Buffer.alloc(0);
    this.speechBuffer = Buffer.alloc(0);
    this.energyHistory = [];
  }

  /**
   * Get current VAD state
   * @returns {Object} Current state information
   */
  getState() {
    return {
      isSpeaking: this.isSpeaking,
      speechDuration: this.speechStartTime ? Date.now() - this.speechStartTime : 0,
      bufferSize: this.speechBuffer.length,
      threshold: this.threshold
    };
  }
}

module.exports = VoiceActivityDetector; 