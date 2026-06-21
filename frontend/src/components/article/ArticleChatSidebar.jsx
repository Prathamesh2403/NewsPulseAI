import React, { useState, useRef, useEffect } from 'react'
import { Sparkles, Send, Loader2 } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { sendArticleChatMessage } from '../../api/articleChatApi'

export function ArticleChatSidebar({ articleId, articleTitle }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: "I've read this article. Ask me anything about it or what the community thinks.",
    },
  ])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef(null)
  const abortRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, isLoading])

  // Cleanup active stream on unmount
  useEffect(() => {
    return () => {
      if (abortRef.current) abortRef.current()
    }
  }, [])

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!inputValue.trim() || isLoading) return

    const userMessage = { role: 'user', content: inputValue.trim() }
    const newHistory = [...messages, userMessage]
    setMessages(newHistory)
    setInputValue('')
    setIsLoading(true)

    // Prepare an empty assistant message slot
    setMessages((prev) => [...prev, { role: 'assistant', content: '' }])

    // Convert history for API (skip the very first greeting if you want, but passing it is fine too)
    const apiHistory = newHistory.slice(1).map((m) => ({
      role: m.role,
      content: m.content,
    }))

    abortRef.current = sendArticleChatMessage(articleId, userMessage.content, apiHistory, {
      onChunk: (textChunk) => {
        setMessages((prev) => {
          const updated = [...prev]
          const lastIndex = updated.length - 1
          if (updated[lastIndex].role === 'assistant') {
            updated[lastIndex] = {
              ...updated[lastIndex],
              content: updated[lastIndex].content + textChunk
            }
          }
          return updated
        })
      },
      onDone: () => {
        setIsLoading(false)
        abortRef.current = null
      },
      onError: (errMsg) => {
        setMessages((prev) => {
          const updated = [...prev]
          const lastIndex = updated.length - 1
          if (updated[lastIndex].role === 'assistant') {
            updated[lastIndex] = {
              ...updated[lastIndex],
              content: updated[lastIndex].content + `\n\n**Error:** ${errMsg}`
            }
          }
          return updated
        })
        setIsLoading(false)
        abortRef.current = null
      },
    })
  }

  return (
    <div className="article-chat-sidebar">
      <div className="article-chat-sidebar__header">
        <Sparkles className="article-chat-sidebar__icon" size={20} />
        <h3>Ask AI</h3>
      </div>

      <div className="article-chat-sidebar__messages">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`article-chat-sidebar__message article-chat-sidebar__message--${msg.role}`}
          >
            <ReactMarkdown>{msg.content}</ReactMarkdown>
          </div>
        ))}
        {isLoading && (
          <div className="article-chat-sidebar__loading">
            <span className="dot"></span>
            <span className="dot"></span>
            <span className="dot"></span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form className="article-chat-sidebar__input-area" onSubmit={handleSubmit}>
        <input
          type="text"
          className="article-chat-sidebar__input"
          placeholder="Ask a question..."
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          disabled={isLoading}
        />
        <button
          type="submit"
          className="article-chat-sidebar__send-btn"
          disabled={!inputValue.trim() || isLoading}
        >
          {isLoading ? <Loader2 size={18} className="spin" /> : <Send size={18} />}
        </button>
      </form>
    </div>
  )
}
