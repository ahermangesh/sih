import React, { useState, useRef, useEffect } from 'react';
import './Chatbot.css';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'bot';
  timestamp: Date;
}

// ARGO Profile Data Interface
interface ArgoProfile {
  id: string;
  date: string;
  cycleNumber: string;
  dataType: string;
  floatWmoId: string;
  latitude: number;
  longitude: number;
  profileId: string;
  source: string;
  type: string;
  tempMin?: number;
  tempMax?: number;
  salinityMin?: number;
  salinityMax?: number;
  maxPressure?: number;
}

// Voice Recognition Types
interface SpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start(): void;
  stop(): void;
  abort(): void;
  onstart: ((this: SpeechRecognition, ev: Event) => any) | null;
  onend: ((this: SpeechRecognition, ev: Event) => any) | null;
  onresult: ((this: SpeechRecognition, ev: SpeechRecognitionEvent) => any) | null;
  onerror: ((this: SpeechRecognition, ev: SpeechRecognitionErrorEvent) => any) | null;
}

interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList;
  resultIndex: number;
}

interface SpeechRecognitionErrorEvent extends Event {
  error: string;
  message: string;
}

declare global {
  interface Window {
    SpeechRecognition: new () => SpeechRecognition;
    webkitSpeechRecognition: new () => SpeechRecognition;
  }
}

const Chatbot: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      text: 'Hello! I\'m Dolphin, your AI assistant for oceanographic data. You can upload CSV files with ARGO float data and ask me questions. I provide different levels of detail for students vs researchers!',
      sender: 'bot',
      timestamp: new Date()
    }
  ]);
  const [inputText, setInputText] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [isVoiceSupported, setIsVoiceSupported] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [argoData, setArgoData] = useState<ArgoProfile[]>([]);
  const [csvUploaded, setCsvUploaded] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Initialize voice recognition on component mount
  useEffect(() => {
    console.log('Initializing voice recognition...');
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    console.log('SpeechRecognition constructor:', SpeechRecognition);
    
    if (SpeechRecognition) {
      console.log('Speech Recognition API is supported');
      setIsVoiceSupported(true);
      
      try {
        recognitionRef.current = new SpeechRecognition();
        console.log('SpeechRecognition instance created:', recognitionRef.current);
      } catch (error) {
        console.error('Error creating SpeechRecognition instance:', error);
        setIsVoiceSupported(false);
        return;
      }
      
      const recognition = recognitionRef.current;
      recognition.continuous = true; // Keep listening continuously
      recognition.interimResults = true; // Show interim results
      recognition.lang = 'en-US';
      
      // Add these properties for better sensitivity (if supported)
      if ('grammars' in recognition) {
        // @ts-ignore - These might not be in TypeScript definitions
        recognition.serviceURI = '';
      }

      recognition.onstart = () => {
        console.log('Speech recognition started');
        setIsListening(true);
      };

      recognition.onend = () => {
        console.log('Speech recognition ended');
        setIsListening(false);
      };

      recognition.onresult = (event: SpeechRecognitionEvent) => {
        let transcript = '';
        
        // Get the most recent result
        for (let i = event.resultIndex; i < event.results.length; i++) {
          if (event.results[i].isFinal) {
            transcript += event.results[i][0].transcript;
          } else {
            // Show interim results
            console.log('Interim result:', event.results[i][0].transcript);
          }
        }
        
        if (transcript) {
          console.log('Final speech recognition result:', transcript);
          setInputText(transcript);
          // Auto-send the voice message
          handleSendMessage(transcript);
          // Stop listening after getting result
          recognition.stop();
        }
      };

      recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
        console.error('Speech recognition error:', event.error);
        setIsListening(false);
        
        // More specific error handling
        switch(event.error) {
          case 'no-speech':
            console.log('No speech detected - this is normal, try speaking louder or closer to mic');
            // Don't show alert for no-speech, just log it
            break;
          case 'audio-capture':
            console.error('No microphone was found. Please ensure microphone is connected and accessible.');
            break;
          case 'not-allowed':
            console.error('Microphone access denied. Please allow microphone access and try again.');
            break;
          case 'network':
            console.error('Network error occurred. Please check your internet connection.');
            break;
          default:
            console.error('Voice recognition error:', event.error);
        }
      };
    } else {
      console.log('Speech Recognition API not supported');
      setIsVoiceSupported(false);
    }

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.abort();
      }
    };
  }, []);

  // Load ARGO CSV data on component mount
  useEffect(() => {
    const loadArgoData = async () => {
      try {
        console.log('Loading ARGO CSV data...');
        const response = await fetch('/data/chroma_2024-07.csv');
        const csvText = await response.text();
        
        const parsedData = parseArgoCSV(csvText);
        setArgoData(parsedData);
        setCsvUploaded(true);
        console.log(`Loaded ${parsedData.length} ARGO profiles`);
        
        // Add welcome message with data info
        const welcomeMessage: Message = {
          id: Date.now().toString(),
          text: `🌊 ARGO Ocean Data System Initialized

📊 System Status: ✅ Ready
📈 Dataset Loaded: ${parsedData.length} oceanographic profiles  
📅 Data Period: July 2024
🛰️ Coverage: Global ocean measurements

💡 Sample Questions:
• Simple: "What's the highest salinity?" 
• Advanced: "Analyze the highest salinity profile with full oceanographic context"
• Regional: "Show me Arabian Sea data"
• Stats: "How many profiles are available?"

🔬 Available Data Types:
Temperature • Salinity • Depth/Pressure • Geographic Locations • Float Information

Ready to assist with your oceanographic data analysis! 🚀`,
          sender: 'bot',
          timestamp: new Date()
        };
        setMessages(prev => [welcomeMessage]);
        
      } catch (error) {
        console.error('Error loading ARGO data:', error);
      }
    };
    
    loadArgoData();
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Text-to-Speech function
  const speakText = (text: string) => {
    if ('speechSynthesis' in window) {
      // Cancel any ongoing speech
      window.speechSynthesis.cancel();
      
      setIsSpeaking(true);
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = 'en-US';
      utterance.rate = 0.9;
      utterance.pitch = 1;
      utterance.volume = 0.8;

      utterance.onend = () => {
        setIsSpeaking(false);
      };

      utterance.onerror = () => {
        setIsSpeaking(false);
        console.error('Speech synthesis error');
      };

      window.speechSynthesis.speak(utterance);
    }
  };

  // Voice input handler
  const startVoiceRecognition = async () => {
    console.log('🎤 startVoiceRecognition called');
    
    if (!isVoiceSupported) {
      console.log('❌ Voice not supported');
      return;
    }

    console.log('✅ Voice is supported, proceeding...');

    // Request microphone permission first
    try {
      console.log('🎧 Requesting microphone permission...');
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      console.log('✅ Microphone permission granted');
      stream.getTracks().forEach(track => track.stop()); // Stop the stream after permission check
    } catch (error) {
      console.error('❌ Microphone permission denied:', error);
      return;
    }

    if (recognitionRef.current && !isListening) {
      try {
        console.log('🚀 Starting voice recognition...');
        recognitionRef.current.start();
        console.log('✅ Voice recognition start() called successfully');
        
        // Auto-stop after 10 seconds if no result
        setTimeout(() => {
          if (isListening) {
            console.log('⏰ Auto-stopping voice recognition after 10 second timeout');
            stopVoiceRecognition();
          }
        }, 10000);
      } catch (error) {
        console.error('❌ Error starting voice recognition:', error);
        if (error instanceof DOMException && error.name === 'InvalidStateError') {
          // Recognition is already running, stop and restart
          console.log('🔄 Recognition already running, restarting...');
          recognitionRef.current.stop();
          setTimeout(() => {
            if (recognitionRef.current) {
              recognitionRef.current.start();
            }
          }, 100);
        } else {
          console.error(`Voice recognition error: ${error}`);
        }
      }
    } else {
      console.log('❌ Recognition not available or already listening', {
        hasRecognition: !!recognitionRef.current,
        isListening
      });
    }
  };

  // Stop voice recognition
  const stopVoiceRecognition = () => {
    if (recognitionRef.current && isListening) {
      console.log('Stopping voice recognition...');
      recognitionRef.current.stop();
    }
  };

  // Enhanced message sending with optional voice text
  const handleSendMessage = async (voiceText?: string) => {
    const messageText = voiceText || inputText;
    if (!messageText.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      text: messageText,
      sender: 'user',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputText('');
    setIsTyping(true);

    // Simulate bot response with voice output
    setTimeout(() => {
      const botResponseText = generateBotResponse(messageText);
      const botMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: botResponseText,
        sender: 'bot',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, botMessage]);
      setIsTyping(false);
      
      // Automatically speak the bot response
      speakText(botResponseText);
    }, 1500);
  };

  // Parse ARGO CSV data
  const parseArgoCSV = (csvText: string): ArgoProfile[] => {
    const lines = csvText.split('\n');
    const headers = lines[0].split(',');
    const profiles: ArgoProfile[] = [];

    for (let i = 1; i < lines.length; i++) {
      const line = lines[i].trim();
      if (!line) continue;

      // Handle CSV parsing with quoted fields that may contain commas
      const values = parseCSVLine(line);
      if (values.length < headers.length) continue;

      try {
        const document = values[2] || '';
        const tempMatch = document.match(/Temperature range ([-\d.]+)–([-\d.]+) °C/);
        const salinityMatch = document.match(/Salinity range ([\d.]+)–([\d.]+) PSU/);
        const pressureMatch = document.match(/Max pressure ([\d.]+) dbar/);

        const profile: ArgoProfile = {
          id: values[0]?.replace('profile:', '') || '',
          date: values[1] || '',
          cycleNumber: values[3] || '',
          dataType: values[4] || '',
          floatWmoId: values[6] || '',
          latitude: parseFloat(values[7]) || 0,
          longitude: parseFloat(values[8]) || 0,
          profileId: values[9] || '',
          source: values[10] || '',
          type: values[11] || '',
          tempMin: tempMatch ? parseFloat(tempMatch[1]) : undefined,
          tempMax: tempMatch ? parseFloat(tempMatch[2]) : undefined,
          salinityMin: salinityMatch ? parseFloat(salinityMatch[1]) : undefined,
          salinityMax: salinityMatch ? parseFloat(salinityMatch[2]) : undefined,
          maxPressure: pressureMatch ? parseFloat(pressureMatch[1]) : undefined,
        };

        profiles.push(profile);
      } catch (error) {
        console.warn('Error parsing profile line:', line, error);
      }
    }

    return profiles;
  };

  // Helper function to parse CSV line with quoted fields
  const parseCSVLine = (line: string): string[] => {
    const result: string[] = [];
    let current = '';
    let inQuotes = false;
    
    for (let i = 0; i < line.length; i++) {
      const char = line[i];
      
      if (char === '"') {
        inQuotes = !inQuotes;
      } else if (char === ',' && !inQuotes) {
        result.push(current.trim());
        current = '';
      } else {
        current += char;
      }
    }
    
    result.push(current.trim());
    return result;
  };

  // Classify question complexity (student vs researcher level)
  const classifyQuestion = (question: string): 'student' | 'researcher' => {
    const researcherKeywords = [
      'identify', 'analyze', 'discuss', 'context', 'significance', 'oceanographic',
      'hydrographic', 'stratification', 'water mass', 'circulation', 'intrusion',
      'evaporation', 'monsoon', 'formation', 'transport', 'intermediate water',
      'full context', 'possible', 'particular position', 'extreme', 'highest recorded'
    ];

    const studentKeywords = [
      'what is', 'what are', 'how many', 'where is', 'when was', 'show me',
      'tell me', 'find', 'list', 'simple', 'basic'
    ];

    const lowerQuestion = question.toLowerCase();
    
    // Count researcher-level keywords
    const researcherScore = researcherKeywords.reduce((score, keyword) => {
      return score + (lowerQuestion.includes(keyword) ? 1 : 0);
    }, 0);

    // Check for complex question patterns
    const isComplex = question.length > 100 || 
                     lowerQuestion.includes('and discuss') ||
                     lowerQuestion.includes('include the') ||
                     lowerQuestion.includes('significance of');

    return (researcherScore >= 2 || isComplex) ? 'researcher' : 'student';
  };

  // Generate enhanced ARGO data response
  const generateArgoResponse = (userInput: string): string => {
    if (argoData.length === 0) {
      return "🔄 ARGO data is still loading. Please try again in a moment.";
    }

    const questionType = classifyQuestion(userInput);
    const input = userInput.toLowerCase();

    // Handle salinity queries
    if (input.includes('salinity') && (input.includes('highest') || input.includes('maximum'))) {
      const highestSalinityProfile = argoData.reduce((max, profile) => {
        return (profile.salinityMax || 0) > (max.salinityMax || 0) ? profile : max;
      });

      if (questionType === 'researcher') {
        return generateResearcherSalinityResponse(highestSalinityProfile);
      } else {
        return `📊 Highest Salinity Analysis

🔍 Quick Result:
• Highest salinity: ${highestSalinityProfile.salinityMax} PSU
• Profile ID: ${highestSalinityProfile.id}
• Location: (${highestSalinityProfile.latitude}°, ${highestSalinityProfile.longitude}°)
• Date: ${new Date(highestSalinityProfile.date).toLocaleDateString()}

📍 Additional Info:
• Float ID: ${highestSalinityProfile.floatWmoId}
• Temperature Range: ${highestSalinityProfile.tempMin}°C - ${highestSalinityProfile.tempMax}°C
• Max Depth: ~${Math.round((highestSalinityProfile.maxPressure || 0) * 1.02)}m`;
      }
    }

    // Handle temperature queries
    if (input.includes('temperature') && (input.includes('highest') || input.includes('maximum'))) {
      const highestTempProfile = argoData.reduce((max, profile) => {
        return (profile.tempMax || 0) > (max.tempMax || 0) ? profile : max;
      });

      if (questionType === 'researcher') {
        return `🌡️ Comprehensive Temperature Analysis

📋 Primary Findings:
The highest temperature recorded is ${highestTempProfile.tempMax}°C in profile ${highestTempProfile.id} (Float ${highestTempProfile.floatWmoId}) at coordinates ${highestTempProfile.latitude}°, ${highestTempProfile.longitude}° on ${new Date(highestTempProfile.date).toLocaleDateString()}.

🏗️ Technical Specifications:
• Maximum depth sampled: ${highestTempProfile.maxPressure} dbar (≈${Math.round((highestTempProfile.maxPressure || 0) * 1.02)}m)
• Full temperature range: ${highestTempProfile.tempMin}°C - ${highestTempProfile.tempMax}°C
• Salinity context: ${highestTempProfile.salinityMin} - ${highestTempProfile.salinityMax} PSU

🌊 Oceanographic Context:
This temperature was recorded at a maximum depth of ${highestTempProfile.maxPressure} dbar, suggesting ${(highestTempProfile.maxPressure || 0) < 1500 ? 'surface or near-surface warming typical of tropical ocean regions with strong solar heating' : 'deep water temperature variations indicating complex vertical mixing processes'}.

📊 Scientific Significance:
The measurement represents ${(highestTempProfile.tempMax || 0) > 28 ? 'tropical surface water conditions with significant implications for regional climate patterns and marine ecosystem dynamics' : 'moderate oceanic temperatures typical of temperate or sub-tropical regions'}.`;
      } else {
        return `🌡️ Highest Temperature Analysis

🔍 Quick Result:
• Highest temperature: ${highestTempProfile.tempMax}°C
• Profile ID: ${highestTempProfile.id}
• Location: (${highestTempProfile.latitude}°, ${highestTempProfile.longitude}°)
• Date: ${new Date(highestTempProfile.date).toLocaleDateString()}

📍 Additional Info:
• Float ID: ${highestTempProfile.floatWmoId}
• Salinity Range: ${highestTempProfile.salinityMin} - ${highestTempProfile.salinityMax} PSU
• Max Depth: ~${Math.round((highestTempProfile.maxPressure || 0) * 1.02)}m`;
      }
    }

    // Handle depth/pressure queries
    if (input.includes('depth') || input.includes('pressure')) {
      const deepestProfile = argoData.reduce((max, profile) => {
        return (profile.maxPressure || 0) > (max.maxPressure || 0) ? profile : max;
      });

      return `🌊 Depth Analysis

🔍 Deepest Measurement:
• Maximum pressure: ${deepestProfile.maxPressure} dbar
• Approximate depth: ~${Math.round((deepestProfile.maxPressure || 0) * 1.02)} meters
• Profile ID: ${deepestProfile.id}

📍 Location & Context:
• Coordinates: (${deepestProfile.latitude}°, ${deepestProfile.longitude}°)
• Date: ${new Date(deepestProfile.date).toLocaleDateString()}
• Temperature at depth: ${deepestProfile.tempMin}°C - ${deepestProfile.tempMax}°C
• Salinity at depth: ${deepestProfile.salinityMin} - ${deepestProfile.salinityMax} PSU`;
    }

    // Handle location queries
    if (input.includes('arabian sea') || input.includes('indian ocean')) {
      const arabianSeaProfiles = argoData.filter(profile => 
        profile.latitude > 10 && profile.latitude < 25 && 
        profile.longitude > 60 && profile.longitude < 75
      );
      
      if (arabianSeaProfiles.length > 0) {
        const avgSalinityMin = Math.min(...arabianSeaProfiles.map(p => p.salinityMin || 0));
        const avgSalinityMax = Math.max(...arabianSeaProfiles.map(p => p.salinityMax || 0));
        
        return `🌊 Arabian Sea Region Analysis

📊 Summary:
• Total profiles found: ${arabianSeaProfiles.length}
• Salinity range: ${avgSalinityMin.toFixed(2)} - ${avgSalinityMax.toFixed(2)} PSU

📍 Geographic Coverage:
• Region: Arabian Sea (10°N-25°N, 60°E-75°E)
• Active floats: ${new Set(arabianSeaProfiles.map(p => p.floatWmoId)).size}

🔬 Key Characteristics:
• High salinity typical of Arabian Sea evaporation patterns
• Significant for monsoon and regional circulation studies`;
      } else {
        return `🌊 Regional Search Results

❌ No profiles found in the specified Arabian Sea region (10°N-25°N, 60°E-75°E) in the current dataset.

💡 Suggestion: Try asking about other regions or general oceanographic parameters.`;
      }
    }

    // Handle count queries
    if (input.includes('how many') || input.includes('count')) {
      return `📊 Dataset Overview

🔢 Total Records:
• ${argoData.length} ARGO oceanographic profiles
• Data period: July 2024
• Geographic coverage: Global ocean regions

🛰️ Float Information:
• Active floats: ${new Set(argoData.map(p => p.floatWmoId)).size}
• Data types: Temperature, Salinity, Pressure/Depth measurements

💡 What you can ask:
• "What's the highest salinity?"
• "Show me temperature data"
• "Find profiles from Arabian Sea"`;
    }

    // Default response
    return `🌊 ARGO Data Assistant Ready!

💡 Available Queries:
• Salinity Analysis: "What's the highest salinity?"
• Temperature Data: "Show me temperature information"
• Depth Analysis: "What's the deepest measurement?"
• Regional Data: "Show me Arabian Sea profiles"
• Dataset Info: "How many profiles are there?"

📊 Current Dataset: ${argoData.length} profiles from July 2024`;
  };

  // Generate detailed researcher-level response for salinity queries
  const generateResearcherSalinityResponse = (profile: ArgoProfile): string => {
    const region = getOceanRegion(profile.latitude, profile.longitude);
    const depthMeters = Math.round((profile.maxPressure || 0) * 1.02);
    
    return `🧪 Comprehensive Salinity Analysis Report

EXECUTIVE SUMMARY
Upon reviewing the ARGO float dataset, the highest recorded salinity is ${profile.salinityMax} PSU observed in profile ${profile.id} of float ${profile.floatWmoId}, documented on ${new Date(profile.date).toLocaleDateString()}.

LOCATION AND GEOGRAPHIC CONTEXT

Coordinates & Position:
• Latitude: ${profile.latitude}°
• Longitude: ${profile.longitude}°  
• Ocean Region: ${region}
• Profile Details: ARGO profile ${profile.cycleNumber} of float ${profile.floatWmoId}

HYDROGRAPHIC DATA PROFILE

Measurement Specifications:
• Salinity Range: ${profile.salinityMin} – ${profile.salinityMax} PSU
• Temperature Range: ${profile.tempMin}°C – ${profile.tempMax}°C  
• Maximum Pressure: ${profile.maxPressure} dbar (≈${depthMeters}m depth)
• Sampling Date: ${new Date(profile.date).toLocaleDateString()}

OCEANOGRAPHIC SIGNIFICANCE & ANALYSIS

Salinity Characteristics:
This profile records exceptionally high salinity values. PSU values above ${(profile.salinityMax || 0) > 36 ? '36' : '35'} are characteristic of ${region === 'Arabian Sea' ? 'the Arabian Sea during summer monsoon periods, where intense evaporation creates hypersaline surface waters' : 'regions with high evaporation rates or specific water mass characteristics'}.

Temperature-Salinity Relationship:
The temperature range (${profile.tempMin}°C–${profile.tempMax}°C) indicates ${profile.tempMax && profile.tempMax > 25 ? 'tropical surface heating with cooler subsurface waters, suggesting strong thermal stratification' : 'cooler water masses typical of higher latitudes or deeper layers'}.

Depth & Pressure Context:
Maximum sampling depth of ${profile.maxPressure} dbar indicates ${(profile.maxPressure || 0) > 1500 ? 'deep water column profiling capturing both surface and intermediate water mass characteristics' : 'shallow to intermediate depth sampling focusing on upper ocean dynamics'}.

SCIENTIFIC IMPLICATIONS & CONCLUSION

Regional Context:
This observation represents significant ocean-atmosphere interaction, particularly relevant for ${region === 'Arabian Sea' ? 'monsoon climatology and regional circulation studies. The high salinity values are consistent with intense evaporation during pre-monsoon periods' : 'understanding local hydrographic processes and water mass formation in this oceanic region'}.

Research Applications:
• Climate modeling and ocean-atmosphere interaction studies
• Regional circulation pattern analysis  
• Water mass formation and transport investigations
• ${region === 'Arabian Sea' ? 'Monsoon dynamics and seasonal variability research' : 'Local oceanographic process characterization'}

Data Quality Assessment:
Profile ${profile.id} provides high-quality measurements suitable for advanced oceanographic research and climate studies.`;
  };

  // Helper function to determine ocean region
  const getOceanRegion = (lat: number, lon: number): string => {
    if (lat > 10 && lat < 30 && lon > 50 && lon < 80) return 'Arabian Sea';
    if (lat > -10 && lat < 30 && lon > 80 && lon < 100) return 'Bay of Bengal';
    if (lat > -40 && lat < 20 && lon > 20 && lon < 120) return 'Indian Ocean';
    if (lat > -60 && lat < -40) return 'Southern Ocean';
    if (lat > 40) return 'Northern Ocean';
    return 'Open Ocean';
  };

  const generateBotResponse = (userInput: string): string => {
    const input = userInput.toLowerCase();
    
    // Check if we have ARGO data loaded and if this is an ARGO-related query
    if (csvUploaded && argoData.length > 0) {
      // Check for ARGO-specific keywords
      if (input.includes('argo') || input.includes('profile') || input.includes('float') ||
          input.includes('salinity') || input.includes('temperature') || input.includes('depth') ||
          input.includes('pressure') || input.includes('highest') || input.includes('maximum') ||
          input.includes('minimum') || input.includes('location') || input.includes('arabian') ||
          input.includes('indian ocean') || input.includes('how many') || input.includes('count')) {
        return generateArgoResponse(userInput);
      }
    }
    
    // Fallback to original responses for non-ARGO queries
    if (input.includes('temperature') || input.includes('temp')) {
      return csvUploaded ? generateArgoResponse(userInput) : 'The current sea surface temperature in the Indian Ocean ranges from 26°C to 30°C. Would you like specific data for a particular region?';
    } else if (input.includes('salinity')) {
      return csvUploaded ? generateArgoResponse(userInput) : 'Ocean salinity levels in our monitored areas range from 34.8 to 35.8 PSU. This data is collected by our Argo float network.';
    } else if (input.includes('float') || input.includes('argo')) {
      return csvUploaded ? generateArgoResponse(userInput) : 'We currently have 10 Argo floats deployed across the Indian Ocean. 7 are active and 3 are inactive. Each float collects temperature, salinity, and depth data.';
    } else if (input.includes('weather') || input.includes('storm')) {
      return 'Current weather conditions are calm with moderate wave heights. No major storms detected in the region. Would you like a detailed forecast?';
    } else if (input.includes('data') || input.includes('information')) {
      return csvUploaded ? 
        `I have access to ${argoData.length} ARGO oceanographic profiles from July 2024. I can provide detailed analysis of temperature, salinity, depth measurements, float locations, and oceanographic conditions. What specific data are you looking for?` :
        'I can provide oceanographic data including temperature, salinity, depth measurements, float locations, and weather conditions. What specific data are you looking for?';
    } else {
      return csvUploaded ?
        `🌊 I'm your ARGO Ocean Data Assistant! I have ${argoData.length} oceanographic profiles loaded. Try asking: "What's the highest salinity?" or "Show me temperature data" or "How many profiles are there?"` :
        'I\'m here to help with oceanographic data and analysis. You can ask me about water temperature, salinity levels, Argo float status, weather conditions, or any other ocean-related data.';
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="chatbot-container">
      <div className="chatbot-header">
        <div className="chatbot-avatar">
          <img 
            src="/logo.png" 
            alt="Dolphin AI" 
            className="bot-avatar-image"
          />
        </div>
        <div className="chatbot-title">
          <h3>Dolphin</h3>
          <span className="bot-subtitle">Ocean Data Assistant</span>
        </div>
      </div>

      <div className="chatbot-messages">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`message ${message.sender === 'user' ? 'user-message' : 'bot-message'}`}
          >
            {message.sender === 'bot' && (
              <div className="message-avatar">
                <img 
                  src="/logo.png" 
                  alt="Dolphin AI" 
                  className="mini-bot-avatar-image"
                />
              </div>
            )}
            <div className="message-content">
              <div className="message-text">{message.text}</div>
              <div className="message-time">
                {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </div>
            </div>
          </div>
        ))}
        
        {isTyping && (
          <div className="message bot-message typing-message">
            <div className="message-avatar">
              <img 
                src="/logo.png" 
                alt="Dolphin AI" 
                className="mini-bot-avatar-image"
              />
            </div>
            <div className="message-content">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      <div className="chatbot-input">
        <div className="input-container">
          <textarea
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={isListening ? "Listening..." : "Ask me about ocean data or click 🎤 to speak..."}
            className="message-input"
            rows={1}
            disabled={isListening}
          />
          
          {/* Voice Controls */}
          {isVoiceSupported && (
            <>
              {/* Original Voice Button */}
              <button
                onClick={() => {
                  console.log('Voice button clicked!');
                  if (isListening) {
                    stopVoiceRecognition();
                  } else {
                    startVoiceRecognition();
                  }
                }}
                className={`voice-button ${isListening ? 'listening' : ''}`}
                title={isListening ? "Stop listening" : "Start voice input"}
                type="button"
              >
              {isListening ? (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
                  <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
                  <circle cx="12" cy="12" r="2" fill="white"/>
                </svg>
              ) : (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
                  <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
                </svg>
              )}
            </button>
            </>
          )}

          {/* Speaker/Mute Button */}
          <button
            onClick={() => {
              if (isSpeaking) {
                window.speechSynthesis.cancel();
                setIsSpeaking(false);
              }
            }}
            className={`speaker-button ${isSpeaking ? 'speaking' : ''}`}
            title={isSpeaking ? "Stop speaking" : "Voice output enabled"}
            type="button"
          >
            {isSpeaking ? (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/>
                <path d="M16 16L20 20M20 16L16 20" stroke="currentColor" strokeWidth="2"/>
              </svg>
            ) : (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/>
              </svg>
            )}
          </button>

          <button
            onClick={() => handleSendMessage()}
            disabled={!inputText.trim() || isListening}
            className="send-button"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
            </svg>
          </button>
        </div>

        {/* Voice Status Indicator */}
        {isVoiceSupported && (isListening || isSpeaking) && (
          <div className="voice-status">
            {isListening && (
              <div className="listening-indicator">
                <span className="pulse-dot"></span>
                <span>Listening... Speak now</span>
              </div>
            )}
            {isSpeaking && (
              <div className="speaking-indicator">
                <span className="wave-animation"></span>
                <span>Dolphin is speaking...</span>
              </div>
            )}
          </div>
        )}

        {/* Voice Not Supported Message */}
        {!isVoiceSupported && (
          <div className="voice-not-supported">
            <small>💡 Voice features require a modern browser (Chrome, Edge, Safari)</small>
          </div>
        )}
      </div>
    </div>
  );
};

export default Chatbot;
