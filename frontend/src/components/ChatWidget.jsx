import React, { useEffect, useRef, useState } from 'react'

const STORAGE_KEY = 'nutriplan_chat'

function loadChatState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch { return null }
}

function saveChatState(state) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)) } catch {}
}

export default function ChatWidget({ appContext, onCommand }) {
  const saved = loadChatState()
  const [open, setOpen] = useState(false)
  const [agentName, setAgentName] = useState(saved?.agentName || '')
  const [nameInput, setNameInput] = useState('')
  const [messages, setMessages] = useState(saved?.messages || [])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    saveChatState({ agentName, messages })
  }, [agentName, messages])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, open])

  const handleNameSubmit = () => {
    const name = nameInput.trim() || 'NutriBot'
    setAgentName(name)
    setMessages([{
      role: 'assistant',
      text: `Hi! I'm ${name}, your personal diet agent 🥦\n\nI can do **everything** for you:\n🔄 **Swap meals** — "Swap my breakfast"\n📝 **Change profile** — "Change my weight to 70"\n🧭 **Navigate** — "Take me to page 2"\n🚫 **Allergies** — "I'm allergic to eggs"\n🍽️ **Nutrition** — Ask me anything about food!\n\nWhat would you like to do?`
    }])
  }

  // Core send function - used by both typed messages and quick reply clicks
  const sendToBackend = async (text, isQuickReply = false) => {
    if (!text || loading) return
    const userMsg = { role: 'user', text: isQuickReply ? text.split('|').pop() || text : text }
    const next = [...messages, userMsg]
    setMessages(next)
    setInput('')
    setLoading(true)

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          history: next.slice(-20).map(m => ({ role: m.role, text: m.text })),
          agentName,
          context: appContext
        })
      })

      if (!res.ok) throw new Error(`Server ${res.status}`)
      const data = await res.json()

      let replyText = data.reply || "Sorry, I couldn't process that."

      // Execute action from backend
      if (data.action && onCommand) {
        try { onCommand(data.action) } catch (e) { console.error("Action failed:", e) }
        // Add indicator
        const actionLabel = {
          SET_VIEW: `📍 Navigated to ${data.action.view || ''}`,
          UPDATE_PROFILE: `✏️ Updated profile`,
          REMOVE_ALLERGEN: `🚫 Removed ${data.action.allergen || ''}`,
          APPLY_SWAP: `🔄 Swapped meal`,
          OPEN_SWAP: `🔄 Opened swap for ${data.action.mealTime || ''}`,
        }[data.action.type] || `⚡ ${data.action.type}`
        replyText += `\n\n${actionLabel}`
      }

      // Also parse any <ACTION> from LLM text
      const actionRegex = /<ACTION>([\s\S]*?)<\/ACTION>/g
      let match
      while ((match = actionRegex.exec(replyText)) !== null) {
        try {
          const a = JSON.parse(match[1])
          if (onCommand) onCommand(a)
        } catch {}
      }
      replyText = replyText.replace(/<ACTION>[\s\S]*?<\/ACTION>/g, '').trim()

      // Build message with optional quickReplies
      const assistantMsg = { role: 'assistant', text: replyText }
      if (data.quickReplies && data.quickReplies.length > 0) {
        assistantMsg.quickReplies = data.quickReplies
      }
      setMessages(prev => [...prev, assistantMsg])
    } catch (err) {
      console.error('[Chat] Error:', err)
      setMessages(prev => [...prev, {
        role: 'assistant',
        text: `Connection error. Make sure backend is running on port 8000.\n\n💡 Run: \`uvicorn app:app --reload --port 8000\``
      }])
    }
    setLoading(false)
  }

  const sendMessage = () => sendToBackend(input.trim())
  const handleKey = (e) => { if (e.key === 'Enter') sendMessage() }
  const handleQuickReply = (qr) => sendToBackend(qr.value, true)

  const formatMessage = (text) => {
    if (!text) return text
    let f = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    f = f.replace(/\n/g, '<br/>')
    f = f.replace(/`([^`]+)`/g, '<code>$1</code>')
    return f
  }

  return (
    <>
      <button className={`chatFab${open ? ' open' : ''}`} onClick={() => setOpen(!open)} title="Chat with your diet companion">
        {open ? '✕' : '🌿'}
      </button>

      {open && (
        <div className="chatWidget">
          {!agentName ? (
            <div style={{ padding: 24, textAlign: 'center' }}>
              <div style={{ fontSize: 48, marginBottom: 12 }}>🥦</div>
              <h3 style={{ margin: '0 0 6px', color: '#1B4332' }}>Name Your Companion</h3>
              <p style={{ margin: '0 0 16px', color: '#717973', fontSize: 13 }}>Your personal diet agent</p>
              <input
                type="text" value={nameInput}
                onChange={e => setNameInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleNameSubmit()}
                placeholder="e.g., NutriBot, Chef, Sage..."
                style={{ width: '100%', height: 42, border: '1px solid #C1C8C2', borderRadius: 10, padding: '0 14px', fontSize: 14, fontFamily: 'inherit', outline: 'none', marginBottom: 12, boxSizing: 'border-box' }}
              />
              <button onClick={handleNameSubmit} style={{ width: '100%', height: 42, border: 'none', borderRadius: 12, background: 'linear-gradient(135deg, #1B4332, #3F665C)', color: '#fff', fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit', fontSize: 14 }}>
                Let's Go! 🚀
              </button>
            </div>
          ) : (
            <>
              <div className="chatHeader">
                <div className="chatAvatar">🥦</div>
                <div className="chatHeaderInfo">
                  <strong>{agentName}</strong>
                  <span>Your diet agent</span>
                </div>
                <button
                  onClick={() => { setAgentName(''); setMessages([]); setNameInput(''); localStorage.removeItem(STORAGE_KEY) }}
                  style={{ marginLeft: 'auto', background: 'none', border: 'none', color: '#fff', cursor: 'pointer', fontSize: 12, opacity: 0.7, padding: '4px 8px' }}
                  title="Reset chat"
                >🔄 Reset</button>
              </div>

              <div className="chatMessages">
                {messages.map((msg, i) => (
                  <div key={i}>
                    <div
                      className={`chatBubble ${msg.role}`}
                      dangerouslySetInnerHTML={msg.role === 'assistant' ? { __html: formatMessage(msg.text) } : undefined}
                    >
                      {msg.role === 'user' ? msg.text : undefined}
                    </div>
                    {/* Quick Reply Buttons */}
                    {msg.role === 'assistant' && msg.quickReplies && msg.quickReplies.length > 0 && (
                      <div className="chatQuickReplies">
                        {msg.quickReplies.map((qr, j) => (
                          <button
                            key={j}
                            className="chatQuickReplyBtn"
                            onClick={() => handleQuickReply(qr)}
                            disabled={loading}
                          >
                            {qr.label}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
                {loading && <div className="chatTyping">💬 {agentName} is thinking...</div>}
                <div ref={bottomRef} />
              </div>

              <div className="chatInputArea">
                <input
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={handleKey}
                  placeholder={`Ask ${agentName} anything...`}
                  disabled={loading}
                />
                <button onClick={sendMessage} disabled={loading}>↑</button>
              </div>
            </>
          )}
        </div>
      )}
    </>
  )
}
