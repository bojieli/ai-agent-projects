import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Mic, MicOff, Trash2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/cjs/styles/prism';
import styles from '../styles/Home.module.css';

interface LogEntry {
  timestamp: number;
  message: string;
  type: 'info' | 'error' | 'latency' | 'llm';
}

interface ChatMessage {
  role: 'user' | 'assistant' | 'transcript';
  content: string;
  isFinal?: boolean;
}

interface TabButtonProps {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}

interface SpeakerInfo {
  speaker: string;
  name: string;
  role: string;
}

const CodeBlock = ({ node, inline, className, children, ...props }) => {
  const match = /language-(\w+)/.exec(className || '');
  const lang = match ? match[1] : '';
  
  if (!inline && lang) {
    return (
      <SyntaxHighlighter
        language={lang}
        style={oneDark}
        customStyle={{
          margin: '0.5em 0',
          borderRadius: '0.375rem',
          fontSize: '0.875rem',
        }}
        {...props}
      >
        {String(children).replace(/\n$/, '')}
      </SyntaxHighlighter>
    );
  }

  return <code className={className} {...props}>{children}</code>;
};

const TabButton: React.FC<TabButtonProps> = ({ active, onClick, children }) => (
  <button
    onClick={onClick}
    className={`flex-1 py-2 text-sm font-medium border-b-2 ${
      active 
        ? 'border-blue-500 text-blue-600' 
        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
    }`}
  >
    {children}
  </button>
);

export default function Home() {
  const [isRecording, setIsRecording] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [isGameStarted, setIsGameStarted] = useState(false);
  const [gameStatus, setGameStatus] = useState('');
  const [currentSpeaker, setCurrentSpeaker] = useState('');
  const [isPlayerTurn, setIsPlayerTurn] = useState(false);
  const websocketRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const sourceNodeRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const workletNodeRef = useRef<AudioWorkletNode | null>(null);
  const echoNodeRef = useRef<AudioWorkletNode | null>(null);
  const audioFormatRef = useRef<any>(null);
  const playbackStartTimeRef = useRef<number | null>(null);
  const vadStartTimeRef = useRef<number | null>(null);
  const vadEndTimeRef = useRef<number | null>(null);
  const speechEndTimeRef = useRef<number | null>(null);
  const hasPlaybackLatencyRef = useRef<boolean>(false);
  const isPlayingRef = useRef<boolean>(false);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [finalTranscripts, setFinalTranscripts] = useState<string>('');
  const currentValidMessageIdRef = useRef<string | null>(null);
  const chatHistoryRef = useRef<HTMLDivElement>(null);
  const logsRef = useRef<HTMLDivElement>(null);
  const shouldAutoScrollChatRef = useRef(true);
  const shouldAutoScrollLogsRef = useRef(true);
  const [activeTab, setActiveTab] = useState<'chat' | 'logs'>('chat');
  const [currentSpeakerInfo, setCurrentSpeakerInfo] = useState<SpeakerInfo | null>(null);
  const [playerRole, setPlayerRole] = useState<string | null>(null);
  const [gamePhase, setGamePhase] = useState<string>('waiting');
  const [notification, setNotification] = useState<string | null>(null);

  const addLog = useCallback((message: string, type: string = 'info') => {
    setLogs(logs => [...logs, `[${type}] ${message}`]);
    // Show important notifications
    if (type === 'info' && !message.startsWith('Transcript:')) {
      setNotification(message);
      setTimeout(() => setNotification(null), 5000);
    }
  }, []);

  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs]);

  const getSpeakerDisplayName = (speakerInfo: SpeakerInfo) => {
    if (speakerInfo.speaker === 'Moderator') {
      return 'Moderator';
    }
    return `${speakerInfo.name} (${speakerInfo.role})`;
  };

  const getSpeakerColor = (role: string) => {
    switch (role) {
      case 'Moderator':
        return '#4a5568'; // Gray
      case 'werewolf':
        return '#e53e3e'; // Red
      case 'seer':
        return '#805ad5'; // Purple
      case 'witch':
        return '#38a169'; // Green
      case 'hunter':
        return '#d69e2e'; // Yellow
      case 'villager':
        return '#3182ce'; // Blue
      default:
        return '#718096'; // Default gray
    }
  };

  const setupWebSocket = () => {
    if (websocketRef.current?.readyState === WebSocket.OPEN) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = process.env.NODE_ENV === 'production' 
      ? window.location.host 
      : 'localhost:3000';
    const ws = new WebSocket(`${protocol}//${host}/ws`);
    websocketRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket connected');
      setIsConnected(true);
      addLog('Connected to server');
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      setIsConnected(false);
      addLog('Disconnected from server');
      
      // Attempt to reconnect after a delay
      setTimeout(setupWebSocket, 2000);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      addLog('WebSocket error occurred', 'error');
    };

    ws.onmessage = async (event) => {
      try {
        if (event.data instanceof Blob) {
          const arrayBuffer = await event.data.arrayBuffer();
          const now = Date.now();

          if (audioFormatRef.current) {
            const int16Array = new Int16Array(arrayBuffer);
            const float32Array = new Float32Array(int16Array.length);
            
            for (let i = 0; i < int16Array.length; i++) {
              float32Array[i] = int16Array[i] / 32768.0;
            }
            
            if (echoNodeRef.current) {
              // Set playback start time when first audio chunk is received
              if (!playbackStartTimeRef.current) {
                playbackStartTimeRef.current = Date.now();
              }

              echoNodeRef.current.port.postMessage({ type: 'unmute' });
              
              if (vadEndTimeRef.current && !hasPlaybackLatencyRef.current) {
                const latency = now - vadEndTimeRef.current;
                const serverVadLatency = now - (speechEndTimeRef.current || vadEndTimeRef.current);
                addLog(`First audio playback latency - Browser VAD: ${latency}ms`, 'latency');
                addLog(`First audio playback latency - Server VAD: ${serverVadLatency}ms`, 'latency');
                hasPlaybackLatencyRef.current = true;
              }
              echoNodeRef.current.port.postMessage(float32Array);
            }
          }
        } else {
          // Handle JSON messages
          const jsonMessage = JSON.parse(event.data);
          
          switch (jsonMessage.type) {
            case 'audio_start':
              handleAudioStart(jsonMessage.format);
              break;
            
            case 'audio_end':
              addLog('Audio streaming completed');
              break;
            
            case 'speaker_info':
              setCurrentSpeakerInfo({
                speaker: jsonMessage.speaker,
                name: jsonMessage.name,
                role: jsonMessage.role
              });
              break;

            case 'game_log':
              addLog(`${jsonMessage.speaker}: ${jsonMessage.message}`);
              break;

            case 'transcript':
              addLog(`Transcript: ${jsonMessage.text}${jsonMessage.isFinal ? ' (final)' : ''}`);
              break;
            
            case 'game_status':
              setGameStatus(jsonMessage.status);
              break;
            
            case 'current_speaker':
              console.log('Current speaker update:', jsonMessage);
              setCurrentSpeaker(jsonMessage.speaker);
              setIsPlayerTurn(jsonMessage.isPlayerTurn);
              break;
            
            case 'game_started':
              setIsGameStarted(true);
              addLog('Game has started!');
              break;
            
            case 'game_ended':
              setIsGameStarted(false);
              addLog(`Game ended! ${jsonMessage.winner} won!`);
              break;

            case 'tts_start':
            case 'tts_complete':
              // These are informational messages, we can log them if needed
              console.log('Audio event:', jsonMessage);
              break;

            default:
              console.log('Unknown message type:', jsonMessage);
          }
        }
      } catch (error) {
        console.error('Error processing message:', error);
        addLog(`Error processing message: ${error}`, 'error');
      }
    };
  };

  useEffect(() => {
    setupWebSocket();

    return () => {
      if (websocketRef.current) {
        websocketRef.current.close();
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, []);

  const handleAudioStart = async (format: any) => {
    console.log('Audio stream starting, format:', format);
    audioFormatRef.current = format;
    
    // Ensure audio context is resumed for playback
    if (audioContextRef.current && audioContextRef.current.state === 'suspended') {
      try {
        await audioContextRef.current.resume();
        console.log('AudioContext resumed for playback');
      } catch (error) {
        console.error('Error resuming AudioContext:', error);
      }
    }
  };

  const startRecording = async () => {
    try {
      // Setup WebSocket first
      setupWebSocket();
      
      // Check if AudioContext and AudioWorklet are supported
      if (!window.AudioContext && !(window as any).webkitAudioContext) {
        throw new Error('AudioContext is not supported in this browser');
      }

      const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
      
      // Create AudioContext with specific sample rate
      audioContextRef.current = new AudioContextClass({
        sampleRate: 16000
      });
      
      // Check if audioWorklet is supported
      if (!audioContextRef.current.audioWorklet) {
        throw new Error('AudioWorklet is not supported in this browser. Please use a modern browser like Chrome or Firefox.');
      }
      
      // Resume the audio context first (needed for some browsers)
      if (audioContextRef.current.state === 'suspended') {
        await audioContextRef.current.resume();
      }
      
      try {
        // Add the audio worklet module with the full URL path
        const workletUrl = new URL('/audioWorklet.js', window.location.origin).href;
        
        // Add a timeout to the worklet loading
        const workletLoadPromise = audioContextRef.current.audioWorklet.addModule(workletUrl);
        const timeoutPromise = new Promise((_, reject) => {
          setTimeout(() => reject(new Error('Audio worklet load timeout')), 5000);
        });
        
        await Promise.race([workletLoadPromise, timeoutPromise]);
        
      } catch (workletError) {
        console.error('Error loading audio worklet:', workletError);
        throw new Error(`Failed to load audio worklet module: ${workletError.message}`);
      }

      // Get user media
      streamRef.current = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        } 
      });

      // Set up audio nodes
      sourceNodeRef.current = audioContextRef.current.createMediaStreamSource(streamRef.current);
      workletNodeRef.current = new AudioWorkletNode(audioContextRef.current, 'audio-processor');
      echoNodeRef.current = new AudioWorkletNode(audioContextRef.current, 'echo-processor');
      
      // Connect nodes: source -> worklet -> destination
      sourceNodeRef.current.connect(workletNodeRef.current);
      echoNodeRef.current.connect(audioContextRef.current.destination);

      // Handle audio data from the worklet
      workletNodeRef.current.port.onmessage = (event) => {
        if (event.data instanceof ArrayBuffer) {
          if (websocketRef.current?.readyState === WebSocket.OPEN) {
            websocketRef.current.send(event.data);
          }
        } else if (event.data.type === 'vad') {
          if (event.data.status === 'speech_start') {
            vadStartTimeRef.current = Date.now();
            addLog('[Frontend VAD] Start of speech detected');
          } else if (event.data.status === 'speech_end') {
            vadEndTimeRef.current = Date.now();
            hasPlaybackLatencyRef.current = false;
            addLog('[Frontend VAD] End of speech detected');
          }
        }
      };

      // Add message handler for the echo node
      echoNodeRef.current.port.onmessage = (event) => {
        if (event.data.type === 'queue_empty' && isPlayingRef.current) {
          isPlayingRef.current = false;
          // Reset playback state
          playbackStartTimeRef.current = null;
          hasPlaybackLatencyRef.current = false;
          addLog('Audio playback completed');
        }
      };

      setIsRecording(true);
    } catch (error) {
      console.error('Error in startRecording:', error);
      addLog(`Error: ${error.message}`, 'error');
      // Clean up any partially initialized resources
      stopRecording();
    }
  };

  const stopRecording = () => {
    if (workletNodeRef.current) {
      workletNodeRef.current.disconnect();
      workletNodeRef.current = null;
    }
    if (echoNodeRef.current) {
      echoNodeRef.current.disconnect();
      echoNodeRef.current = null;
    }
    if (sourceNodeRef.current) {
      sourceNodeRef.current.disconnect();
      sourceNodeRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    setIsRecording(false);
  };

  const startGame = async () => {
    try {
      await setupAudioWithRetry();
      await startRecording();
      
      if (websocketRef.current?.readyState === WebSocket.OPEN) {
        websocketRef.current.send(JSON.stringify({
          type: 'start_game',
          playerId: 'human_player'
        }));
      }
    } catch (error) {
      console.error('Failed to start game:', error);
      addLog('Error: Failed to start game. Please refresh and try again.', 'error');
    }
  };

  // Move setupAudio and setupAudioWithRetry outside useEffect
  const setupAudio = async () => {
    try {
      console.log('Requesting initial microphone permission...');
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });
      // Stop the stream immediately, we'll recreate it when needed
      stream.getTracks().forEach(track => track.stop());
      console.log('Microphone permission granted');

      // Initialize audio context
      audioContextRef.current = new AudioContext();
      console.log('AudioContext created');
      
      // Resume audio context (browsers require user interaction)
      if (audioContextRef.current.state === 'suspended') {
        await audioContextRef.current.resume();
        console.log('AudioContext resumed');
      }
      
      // Load audio worklet
      try {
        const baseUrl = window.location.origin;
        const workletUrl = `${baseUrl}/audioWorklet.js`;
        console.log('Loading audio worklet module from:', workletUrl);
        
        // Wait for the module to load
        await audioContextRef.current.audioWorklet.addModule(workletUrl);
        console.log('AudioWorklet module loaded successfully');

        // Create the echo processor node
        console.log('Creating echo processor...');
        if (!audioContextRef.current) {
          throw new Error('Audio context was closed');
        }
        
        echoNodeRef.current = new AudioWorkletNode(audioContextRef.current, 'echo-processor', {
          numberOfInputs: 1,
          numberOfOutputs: 1,
          outputChannelCount: [1]
        });
        
        if (!echoNodeRef.current) {
          throw new Error('Failed to create echo processor node');
        }
        
        echoNodeRef.current.connect(audioContextRef.current.destination);
        echoNodeRef.current.port.postMessage({ type: 'setSpeed', speed: 0.4 });
        console.log('Echo processor created and connected successfully');
        
        // Add error handler for the worklet
        echoNodeRef.current.port.onmessageerror = (event) => {
          console.error('Error in echo processor:', event);
        };
      } catch (workletError) {
        console.error('Error loading audio worklet:', workletError);
        throw new Error(`Failed to initialize audio worklet: ${workletError.message}`);
      }
    } catch (error) {
      console.error('Error setting up audio:', error);
      addLog(`Error: Audio setup failed - ${error.message}. Please refresh and try again.`, 'error');
      throw error;
    }
  };

  const setupAudioWithRetry = async (retries = 3) => {
    for (let i = 0; i < retries; i++) {
      try {
        await setupAudio();
        return;
      } catch (error) {
        console.error(`Audio setup attempt ${i + 1} failed:`, error);
        if (i === retries - 1) {
          addLog('Error: Failed to set up audio after multiple attempts. Please refresh the page.', 'error');
          throw error;
        } else {
          await new Promise(resolve => setTimeout(resolve, 1000));
        }
      }
    }
  };

  // Add cleanup when game ends
  useEffect(() => {
    if (!isGameStarted && isRecording) {
      console.log('Game ended, stopping recording...');
      stopRecording();
    }
  }, [isGameStarted]);

  return (
    <div className={styles.container}>
      {notification && (
        <div className={styles.notification}>
          {notification}
        </div>
      )}
      <main className={styles.main}>
        <h1 className={styles.title}>
          Werewolf Live Audio Game
        </h1>

        <div className={styles.gameControls}>
          {!isGameStarted ? (
            <button 
              className={`${styles.button} ${styles.buttonStart}`}
              onClick={startGame}
              disabled={!isConnected}
            >
              {isConnected ? 'Start New Game' : 'Connecting...'}
            </button>
          ) : (
            <div className={styles.gameStatus}>
              <div className={styles.statusGrid}>
                <div className={styles.statusItem}>
                  <h3>Game Phase</h3>
                  <p>{gamePhase}</p>
                </div>
                <div className={styles.statusItem}>
                  <h3>Your Role</h3>
                  <p style={{ color: playerRole ? getSpeakerColor(playerRole) : 'inherit' }}>
                    {playerRole || 'Not assigned'}
                  </p>
                </div>
                <div className={styles.statusItem}>
                  <h3>Current Speaker</h3>
                  <p>{currentSpeakerInfo ? getSpeakerDisplayName(currentSpeakerInfo) : ''}</p>
                </div>
              </div>
              
              <div className={styles.debugInfo}>
                <p>Is Player Turn: {isPlayerTurn ? 'Yes' : 'No'}</p>
                <p>Current Speaker: {currentSpeaker}</p>
                <p>Recording Status: {isRecording ? 'Active' : 'Inactive'}</p>
              </div>
            </div>
          )}
        </div>

        <div className={styles.logs}>
          <div className={styles.logsHeader}>
            <h2>Game Log</h2>
          </div>
          <div className={styles.logContent}>
            {logs.map((log, index) => {
              if (currentSpeakerInfo && !log.startsWith('[latency]')) {
                const color = getSpeakerColor(currentSpeakerInfo.role);
                return (
                  <div key={index} className={styles.logEntry} style={{ borderLeft: `4px solid ${color}` }}>
                    <span className={styles.speakerName} style={{ color }}>
                      {getSpeakerDisplayName(currentSpeakerInfo)}
                    </span>
                    <span className={styles.logMessage}>
                      {log.replace(/^\[[^\]]+\]\s*/, '')}
                    </span>
                  </div>
                );
              }
              return (
                <div key={index} className={styles.logEntry}>
                  <span className={styles.logMessage}>{log}</span>
                </div>
              );
            })}
            <div ref={logsEndRef} />
          </div>
        </div>
      </main>
    </div>
  );
}
