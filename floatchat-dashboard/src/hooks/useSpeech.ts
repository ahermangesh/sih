'use client'

import { useState, useRef, useCallback, useEffect } from 'react'

// Define types for Web Speech API
interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList
  resultIndex: number
}

interface SpeechRecognition extends EventTarget {
  continuous: boolean
  interimResults: boolean
  lang: string
  start(): void
  stop(): void
  abort(): void
  onstart: ((this: SpeechRecognition, ev: Event) => any) | null
  onresult: ((this: SpeechRecognition, ev: SpeechRecognitionEvent) => any) | null
  onend: ((this: SpeechRecognition, ev: Event) => any) | null
  onerror: ((this: SpeechRecognition, ev: Event) => any) | null
}

declare global {
  interface Window {
    SpeechRecognition: {
      new (): SpeechRecognition
    }
    webkitSpeechRecognition: {
      new (): SpeechRecognition
    }
  }
}

export interface UseSpeechResult {
  // Speech Recognition
  isListening: boolean
  transcript: string
  startListening: () => void
  stopListening: () => void
  resetTranscript: () => void
  
  // Text-to-Speech
  isSpeaking: boolean
  speak: (text: string) => void
  stopSpeaking: () => void
  
  // Support detection
  speechSupported: boolean
  ttsSupported: boolean
}

export function useSpeech(): UseSpeechResult {
  const [isListening, setIsListening] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [isSpeaking, setIsSpeaking] = useState(false)
  
  const recognitionRef = useRef<SpeechRecognition | null>(null)
  const speechSynthesisRef = useRef<SpeechSynthesisUtterance | null>(null)

  // Check browser support
  const speechSupported = typeof window !== 'undefined' && 
    ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window)
  
  const ttsSupported = typeof window !== 'undefined' && 
    'speechSynthesis' in window

  // Initialize speech recognition
  useEffect(() => {
    if (!speechSupported) return

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    const recognition = new SpeechRecognition()
    
    recognition.continuous = true
    recognition.interimResults = true
    recognition.lang = 'en-US'

    recognition.onstart = () => {
      setIsListening(true)
    }

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let finalTranscript = ''
      let interimTranscript = ''

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i]
        if (result.isFinal) {
          finalTranscript += result[0].transcript
        } else {
          interimTranscript += result[0].transcript
        }
      }

      setTranscript(finalTranscript + interimTranscript)
    }

    recognition.onend = () => {
      setIsListening(false)
    }

    recognition.onerror = (event: any) => {
      console.error('Speech recognition error:', event.error)
      setIsListening(false)
    }

    recognitionRef.current = recognition

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.abort()
      }
    }
  }, [speechSupported])

  const startListening = useCallback(() => {
    if (!speechSupported || !recognitionRef.current || isListening) return
    
    setTranscript('')
    recognitionRef.current.start()
  }, [speechSupported, isListening])

  const stopListening = useCallback(() => {
    if (!recognitionRef.current || !isListening) return
    
    recognitionRef.current.stop()
  }, [isListening])

  const resetTranscript = useCallback(() => {
    setTranscript('')
  }, [])

  const speak = useCallback((text: string) => {
    if (!ttsSupported || !text.trim()) return

    // Stop any ongoing speech
    window.speechSynthesis.cancel()

    const utterance = new SpeechSynthesisUtterance(text)
    utterance.rate = 0.9
    utterance.pitch = 1
    utterance.volume = 1

    utterance.onstart = () => {
      setIsSpeaking(true)
    }

    utterance.onend = () => {
      setIsSpeaking(false)
    }

    utterance.onerror = () => {
      setIsSpeaking(false)
    }

    speechSynthesisRef.current = utterance
    window.speechSynthesis.speak(utterance)
  }, [ttsSupported])

  const stopSpeaking = useCallback(() => {
    if (!ttsSupported) return
    
    window.speechSynthesis.cancel()
    setIsSpeaking(false)
  }, [ttsSupported])

  return {
    // Speech Recognition
    isListening,
    transcript,
    startListening,
    stopListening,
    resetTranscript,
    
    // Text-to-Speech
    isSpeaking,
    speak,
    stopSpeaking,
    
    // Support detection
    speechSupported,
    ttsSupported,
  }
}