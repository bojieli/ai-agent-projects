class AudioProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.inputBuffer = [];
    
    // VAD parameters
    this.energyThreshold = 0.0001;  // Adjust this threshold based on testing
    this.isSpeaking = false;
    this.silenceStartTime = null;
    this.requiredSilenceMs = 100;  // 100ms silence for speech end
    this.consecutiveSilentFrames = 0;
    this.lastFrameTime = null;
    
    // Debug counters
    this.processCallCount = 0;
    this.lastDebugTime = Date.now();

    // Send initial message to confirm processor is created
    this.port.postMessage({ 
      type: 'debug', 
      message: 'AudioProcessor initialized' 
    });
  }

  calculateEnergy(samples) {
    let sum = 0;
    for (let i = 0; i < samples.length; i++) {
      sum += samples[i] * samples[i];
    }
    return sum / samples.length;
  }

  process(inputs, outputs, parameters) {
    const input = inputs[0];
    if (!input || !input[0] || input[0].length === 0) {
      this.port.postMessage({ 
        type: 'debug', 
        message: 'No input data received' 
      });
      return true;
    }

    // Debug input data
    const inputChannel = input[0];
    let maxAmp = 0;
    for (let i = 0; i < inputChannel.length; i++) {
      maxAmp = Math.max(maxAmp, Math.abs(inputChannel[i]));
    }
    
    // Log input levels periodically
    this.processCallCount++;
    const now = Date.now();
    if (now - this.lastDebugTime > 1000) {
      this.port.postMessage({ 
        type: 'debug', 
        message: `Process called ${this.processCallCount} times, max amplitude: ${maxAmp}` 
      });
      this.processCallCount = 0;
      this.lastDebugTime = now;
    }

    // Convert to mono if multiple channels
    const monoInput = new Float32Array(input[0].length);
    for (let i = 0; i < input[0].length; i++) {
      let sum = 0;
      for (let channel = 0; channel < input.length; channel++) {
        sum += input[channel][i];
      }
      monoInput[i] = sum / input.length;
    }

    // Copy input to output to enable monitoring
    const output = outputs[0];
    for (let channel = 0; channel < output.length; channel++) {
      output[channel].set(monoInput);
    }

    // VAD processing
    const energy = this.calculateEnergy(monoInput);
    const currentTime = Date.now();
    
    if (energy > this.energyThreshold) {
      // Reset silence detection when energy goes above threshold
      this.consecutiveSilentFrames = 0;
      this.silenceStartTime = null;
      
      if (!this.isSpeaking) {
        this.isSpeaking = true;
        this.port.postMessage({ type: 'vad', status: 'speech_start' });
      }
    } else if (this.isSpeaking) {
      // Track consecutive silent frames
      if (this.silenceStartTime === null) {
        this.silenceStartTime = currentTime;
      }
      
      // Ensure we're getting continuous frames
      if (this.lastFrameTime && (currentTime - this.lastFrameTime) > 50) {
        // Frame gap too large, reset silence detection
        this.consecutiveSilentFrames = 0;
        this.silenceStartTime = currentTime;
      }
      
      this.consecutiveSilentFrames++;
      
      // Check if we have enough consecutive silent frames
      const silenceDuration = currentTime - this.silenceStartTime;
      if (silenceDuration >= this.requiredSilenceMs) {
        this.isSpeaking = false;
        this.silenceStartTime = null;
        this.consecutiveSilentFrames = 0;
        this.port.postMessage({ type: 'vad', status: 'speech_end' });
      }
    }
    
    this.lastFrameTime = currentTime;

    // Process in chunks
    const CHUNK_SIZE = 1024;
    this.inputBuffer.push(...monoInput);

    while (this.inputBuffer.length >= CHUNK_SIZE) {
      const chunk = this.inputBuffer.slice(0, CHUNK_SIZE);
      this.inputBuffer = this.inputBuffer.slice(CHUNK_SIZE);

      // Convert to 16-bit PCM
      const pcmData = new Int16Array(chunk.length);
      for (let i = 0; i < chunk.length; i++) {
        const s = Math.max(-1, Math.min(1, chunk[i]));
        pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
      }

      // Send the data if non-zero
      let maxAbsPCM = 0;
      for (let i = 0; i < pcmData.length; i++) {
        maxAbsPCM = Math.max(maxAbsPCM, Math.abs(pcmData[i]));
      }
      
      if (maxAbsPCM > 0) {
        this.port.postMessage(pcmData.buffer, [pcmData.buffer]);
      }
    }

    return true;
  }
}

class EchoProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.audioBuffer = [];
    this.playbackPosition = 0;
    this.isPlaying = false;
    this.sampleRate = 16000;  // Input sample rate
    this.isMuted = false;
    this.outputBufferSize = 2048;
    this.outputBuffer = new Float32Array(this.outputBufferSize);
    this.outputBufferPosition = 0;
    this.hasNotifiedQueueEmpty = false;
    this.playbackSpeed = 0.5;  // Slow down playback to 0.5x speed
    
    this.port.onmessage = (event) => {
      if (event.data instanceof Float32Array) {
        if (!this.isMuted) {
          const audioData = event.data;
          const newBuffer = new Float32Array(audioData.length);
          newBuffer.set(audioData);
          
          if (!this.isPlaying) {
            this.audioBuffer = Array.from(newBuffer);
            this.playbackPosition = 0;
            this.outputBufferPosition = 0;
            this.hasNotifiedQueueEmpty = false;
          } else {
            this.audioBuffer.push(...Array.from(newBuffer));
          }
          
          this.isPlaying = true;
        }
      } else if (event.data.type === 'clear') {
        this.audioBuffer = [];
        this.playbackPosition = 0;
        this.outputBufferPosition = 0;
        this.isPlaying = false;
        this.isMuted = true;
        this.hasNotifiedQueueEmpty = false;
        this.port.postMessage({ type: 'queue_empty' });
      } else if (event.data.type === 'unmute') {
        this.isMuted = false;
        this.hasNotifiedQueueEmpty = false;
      } else if (event.data.type === 'mute') {
        this.isMuted = true;
        this.audioBuffer = [];
        this.playbackPosition = 0;
        this.isPlaying = false;
        this.hasNotifiedQueueEmpty = false;
        this.port.postMessage({ type: 'queue_empty' });
      } else if (event.data.type === 'setSpeed') {
        this.playbackSpeed = event.data.speed;
      }
    };
  }

  process(inputs, outputs, parameters) {
    const output = outputs[0];
    
    if (this.isMuted || !this.isPlaying || this.audioBuffer.length === 0) {
      for (let channel = 0; channel < output.length; channel++) {
        output[channel].fill(0);
      }
      
      if (this.isPlaying && !this.hasNotifiedQueueEmpty) {
        this.port.postMessage({ type: 'queue_empty' });
        this.hasNotifiedQueueEmpty = true;
        this.isPlaying = false;
      }
      
      return true;
    }

    const outputChannel = output[0];
    const bufferSize = outputChannel.length;
    
    if (this.isPlaying && this.audioBuffer.length > 0) {
      // Interpolate samples for speed adjustment
      for (let i = 0; i < bufferSize; i++) {
        const position = Math.floor(this.playbackPosition);
        if (position < this.audioBuffer.length) {
          // Linear interpolation for smoother playback
          const fraction = this.playbackPosition - position;
          const currentSample = this.audioBuffer[position];
          const nextSample = position + 1 < this.audioBuffer.length ? 
            this.audioBuffer[position + 1] : currentSample;
          
          const interpolatedSample = currentSample + fraction * (nextSample - currentSample);
          
          for (let channel = 0; channel < output.length; channel++) {
            output[channel][i] = interpolatedSample;
          }
          
          this.playbackPosition += this.playbackSpeed;
        } else {
          for (let channel = 0; channel < output.length; channel++) {
            output[channel][i] = 0;
          }
          
          if (!this.hasNotifiedQueueEmpty) {
            this.isPlaying = false;
            this.playbackPosition = 0;
            this.audioBuffer = [];
            this.port.postMessage({ type: 'queue_empty' });
            this.hasNotifiedQueueEmpty = true;
          }
        }
      }
    } else {
      for (let channel = 0; channel < output.length; channel++) {
        output[channel].fill(0);
      }
    }

    return true;
  }
}

registerProcessor('audio-processor', AudioProcessor);
registerProcessor('echo-processor', EchoProcessor);
