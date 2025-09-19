'use client'

import { useState, useRef, useEffect } from 'react'
import type { ChatMessage } from '@/types'
import { useDashboard } from '@/context/DashboardContext'
import { useSpeech } from '@/hooks/useSpeech'

// Mock messages for development
const mockMessages: ChatMessage[] = [
  {
    id: '1',
    content: 'Hello! I\'m FloatChat, your AI assistant for exploring ocean data. Ask me anything about ARGO floats, temperature profiles, or oceanographic conditions! Currently showing Indian Ocean data.',
    role: 'assistant',
    timestamp: new Date(Date.now() - 5 * 60 * 1000),
  },
]

export default function ChatPanel() {
  const [messages, setMessages] = useState<ChatMessage[]>(mockMessages)
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [conversationId] = useState(() => `conv_${Date.now()}_${Math.random().toString(36).substring(2)}`)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  
  // Dashboard context integration
  const { setFromChatQuery, filter } = useDashboard()

  // Speech functionality
  const { 
    isListening, 
    transcript, 
    startListening, 
    stopListening, 
    resetTranscript,
    speak,
    stopSpeaking,
    isSpeaking,
    speechSupported,
    ttsSupported 
  } = useSpeech()

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Update input when speech transcript changes
  useEffect(() => {
    if (transcript) {
      setInput(transcript)
    }
  }, [transcript])

  // Speech recognition handlers
  const handleMicrophoneClick = () => {
    if (isListening) {
      stopListening()
    } else {
      resetTranscript()
      setInput('')
      startListening()
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      content: input.trim(),
      role: 'user',
      timestamp: new Date(),
    }

    setMessages(prev => [...prev, userMessage])
    const currentInput = input.trim()
    setInput('')
    setIsLoading(true)

    // Update dashboard context based on user query
    setFromChatQuery(currentInput)

    try {
      // Import API service dynamically to avoid SSR issues
      const apiService = (await import('@/lib/api')).default
      const response = await apiService.sendChatMessage(currentInput, conversationId)
      setMessages(prev => [...prev, response])
      
      // Automatically speak the response if TTS is supported
      if (ttsSupported && response.content) {
        setTimeout(() => speak(response.content), 500) // Small delay to ensure UI updates first
      }
    } catch (error) {
      console.error('Failed to send message:', error)
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        content: 'Sorry, I encountered an error processing your request. Please check if the backend server is running on localhost:8000 and try again.',
        role: 'assistant',
        timestamp: new Date(),
        metadata: {
          query_type: 'error',
          confidence: 0,
          data_sources: [],
          processing_time: 0,
          error: true
        },
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Header - Modern Clean Design */}
      <div className="border-b border-gray-100 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            {/* Modern Avatar */}
            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center shadow-sm">
              <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
              </svg>
            </div>
            <div>
              <h2 className="font-medium text-gray-900 text-sm">
                FloatChat Assistant
              </h2>
              <div className="flex items-center space-x-1">
                <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                <span className="text-xs text-gray-500">
                  Online
                </span>
              </div>
            </div>
          </div>
          
          {/* Audio Controls - Modern Icons */}
          <div className="flex items-center space-x-1">
            {isSpeaking && (
              <button
                onClick={stopSpeaking}
                className="p-2 text-gray-400 hover:text-red-500 hover:bg-gray-50 rounded-lg transition-all duration-150"
                title="Stop speaking"
              >
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M9.383 3.076A1 1 0 0110 4v12a1 1 0 01-1.617.772L6.646 15H4a1 1 0 01-1-1V6a1 1 0 011-1h2.646l1.737-1.228a1 1 0 011-.696zM12 5a1 1 0 011.414 0L15 6.586l1.586-1.586A1 1 0 0118 6.414L16.414 8 18 9.586A1 1 0 0116.586 11L15 9.414 13.414 11A1 1 0 0112 9.586L13.586 8 12 6.414A1 1 0 0112 5z" clipRule="evenodd" />
                </svg>
              </button>
            )}
            
            {/* Speech Support Indicators */}
            <div className="flex space-x-1">
              {speechSupported && (
                <div className="px-2 py-1 bg-green-50 text-green-600 text-xs rounded-md font-medium" title="Speech recognition available">
                  <svg className="w-3 h-3 inline mr-1" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M7 4a3 3 0 016 0v4a3 3 0 11-6 0V4zm4 10.93A7.001 7.001 0 0017 8a1 1 0 10-2 0A5 5 0 015 8a1 1 0 00-2 0 7.001 7.001 0 006 6.93V17H6a1 1 0 100 2h8a1 1 0 100-2h-3v-2.07z" clipRule="evenodd" />
                  </svg>
                  Mic
                </div>
              )}
              {ttsSupported && (
                <div className="px-2 py-1 bg-blue-50 text-blue-600 text-xs rounded-md font-medium" title="Text-to-speech available">
                  <svg className="w-3 h-3 inline mr-1" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M9.383 3.076A1 1 0 0110 4v12a1 1 0 01-1.617.772L6.646 15H4a1 1 0 01-1-1V6a1 1 0 011-1h2.646l1.737-1.228a1 1 0 011-.696zM15.657 6.343a1 1 0 011.414 0A9.972 9.972 0 0119 10a9.972 9.972 0 01-1.929 3.657 1 1 0 01-1.414-1.414A7.971 7.971 0 0017 10c0-.886-.163-1.734-.464-2.514a1 1 0 010-1.143z" clipRule="evenodd" />
                  </svg>
                  Audio
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Messages - Clean Modern Design */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div className={`flex max-w-[80%] ${message.role === 'user' ? 'flex-row-reverse' : 'flex-row'} items-start space-x-3`}>
              {/* Avatar */}
              <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                message.role === 'user' 
                  ? 'bg-gray-100 ml-3' 
                  : 'bg-gradient-to-br from-blue-500 to-purple-600 mr-3'
              }`}>
                {message.role === 'user' ? (
                  <svg className="w-4 h-4 text-gray-600" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
                  </svg>
                ) : (
                  <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
                  </svg>
                )}
              </div>
              
              {/* Message Content */}
              <div className="flex flex-col">
                {message.role === 'user' ? (
                  // User message with pastel container
                  <div className="bg-blue-100 text-gray-900 rounded-2xl px-4 py-3 shadow-sm">
                    <p className="text-sm leading-relaxed font-medium">{message.content}</p>
                    {message.metadata && (
                      <div className="mt-2">
                        <span className="bg-white/60 px-2 py-1 rounded text-xs text-gray-600">
                          {Math.round((message.metadata.confidence || 0) * 100)}% confidence
                        </span>
                      </div>
                    )}
                  </div>
                ) : (
                  // Assistant message without container - just text
                  <div className="flex items-start">
                    <div>
                      <p className="text-sm leading-relaxed text-gray-900 font-medium">{message.content}</p>
                      {/* Text-to-Speech button for assistant messages */}
                      {ttsSupported && (
                        <button
                          onClick={() => speak(message.content)}
                          disabled={isSpeaking}
                          className={`mt-2 p-1.5 rounded-lg hover:bg-gray-100 transition-colors ${
                            isSpeaking ? 'text-blue-500' : 'text-gray-400 hover:text-gray-600'
                          }`}
                          title={isSpeaking ? 'Speaking...' : 'Read aloud'}
                        >
                          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M9.383 3.076A1 1 0 0110 4v12a1 1 0 01-1.617.772L6.646 15H4a1 1 0 01-1-1V6a1 1 0 011-1h2.646l1.737-1.228a1 1 0 011-.696z" clipRule="evenodd" />
                            <path d="M11.425 12.769l3.433 3.433c.442-.313.822-.689 1.134-1.134l-3.433-3.433c-.442.313-.822.689-1.134 1.134zM15.95 10.050l1.414-1.414A8 8 0 0010 2a8 8 0 00-7.364 6.636l1.414 1.414a6 6 0 0111.9 0z" />
                          </svg>
                        </button>
                      )}
                    </div>
                  </div>
                )}
                
                {/* Time below the message */}
                <div className={`mt-2 text-xs text-gray-500 ${message.role === 'user' ? 'text-right' : 'text-left'}`}>
                  {formatTime(message.timestamp)}
                </div>
              </div>
            </div>
          </div>
        ))}

        {/* Loading State - No Container */}
        {isLoading && (
          <div className="flex justify-start">
            <div className="flex items-start space-x-3">
              <div className="flex-shrink-0 w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center">
                <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="flex flex-col">
                <div className="flex items-center space-x-2">
                  <div className="flex space-x-1">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                  </div>
                  <span className="text-sm text-gray-500 font-medium">
                    FloatChat is thinking...
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input - Modern Clean Design */}
      <div className="border-t border-gray-100 px-6 py-4">
        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="flex items-end space-x-3">
            <div className="flex-1 relative">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={isListening ? "🎤 Listening..." : "Type your message about ocean data..."}
                className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-2xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-150 text-sm placeholder-gray-500 text-gray-900"
                disabled={isLoading}
              />
            </div>
            
            {/* Microphone Button - Modern */}
            {speechSupported && (
              <button
                type="button"
                onClick={handleMicrophoneClick}
                className={`p-3 rounded-2xl transition-all duration-150 ${
                  isListening 
                    ? 'bg-red-500 hover:bg-red-600 text-white shadow-md' 
                    : 'bg-gray-100 hover:bg-gray-200 text-gray-600'
                }`}
                title={isListening ? 'Stop listening' : 'Start voice input'}
              >
                {isListening ? (
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8 7a1 1 0 00-1 1v4a1 1 0 001 1h4a1 1 0 001-1V8a1 1 0 00-1-1H8z" clipRule="evenodd" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M7 4a3 3 0 016 0v4a3 3 0 11-6 0V4zm4 10.93A7.001 7.001 0 0017 8a1 1 0 10-2 0A5 5 0 015 8a1 1 0 00-2 0 7.001 7.001 0 006 6.93V17H6a1 1 0 100 2h8a1 1 0 100-2h-3v-2.07z" clipRule="evenodd" />
                  </svg>
                )}
              </button>
            )}
            
            {/* Send Button - Modern */}
            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              className="p-3 bg-blue-500 hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed text-white rounded-2xl transition-all duration-150 shadow-md hover:shadow-lg"
            >
              {isLoading ? (
                <svg className="w-5 h-5 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              ) : (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              )}
            </button>
          </div>
          
          {/* Speech status indicator - Modern */}
          {isListening && (
            <div className="flex items-center justify-center space-x-2 text-sm text-gray-600 bg-red-50 rounded-xl py-2 px-4">
              <div className="flex space-x-1">
                <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
                <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }}></div>
                <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" style={{ animationDelay: '0.4s' }}></div>
              </div>
              <span className="font-medium">Recording... Speak now or click stop</span>
            </div>
          )}
        </form>
      </div>
    </div>
  )
}
