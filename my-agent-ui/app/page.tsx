"use client";
import { useEffect } from "react";
import { useStream } from "@langchain/langgraph-sdk/react";
import type { Message } from "@langchain/langgraph-sdk";

// Helper to prevent React crashes if the agent sends an object/array instead of a plain string
const renderContent = (content: any): string => {
  if (typeof content === "string") return content;
  if (Array.isArray(content)) {
    return content.map(c => (typeof c === "string" ? c : JSON.stringify(c))).join(" ");
  }
  return JSON.stringify(content);
};

export default function ChatPage() {
  // Connect directly to your LangGraph Agent Protocol server
  const chat = useStream<{ messages: Message[] }>({
    apiUrl: "http://localhost:8000",
    assistantId: "agent",
  });

  useEffect(() => {
    // Only trigger if no messages and not already loading
    if (chat.messages?.length === 0 && !chat.isLoading) {
      chat.submit({});
    }
  }, [chat.messages?.length, chat.isLoading, chat.submit]);

  const handleSend = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const text = formData.get("message") as string;

    if (text.trim()) {
      chat.submit({
        messages: [{ type: "human", content: text }],
      });
      e.currentTarget.reset();
    }
  };

  return (
    // Clean white background, black default text
    <div className="flex flex-col h-screen max-w-3xl mx-auto p-4 font-sans bg-white text-black">
      {/* Header */}
      <h1 className="text-2xl font-bold mb-4 border-b border-gray-300 pb-4">
        My LangGraph Agent
      </h1>

      {/* --- CHAT MESSAGES AREA --- */}
      <div className="flex-1 overflow-y-auto mb-4 space-y-6 pr-2">
        {chat.messages?.map((msg, idx) => {
          // Safely extract your custom Python options from the message metadata
          // We cast to 'any' here to prevent strict TypeScript errors
          const msgAny = msg as any;
          const options =
            msgAny.additional_kwargs?.metadata?.options ||
            msgAny.additional_kwargs?.options ||
            null;

          return (
            <div
              key={msg.id || idx}
              // Using distinct boxes with borders for both user and agent
              className={`p-5 rounded-xl border shadow-sm ${
                msg.type === "human"
                  ? "bg-gray-50 border-gray-300 ml-auto max-w-[85%]" // User box: slightly gray background
                  : "bg-white border-gray-400 mr-auto max-w-[85%]" // Agent box: pure white background
              }`}
            >
              <strong className="text-xs uppercase tracking-wider text-gray-500 mb-2 block">
                {msg.type === "human" ? "You" : "Agent"}
              </strong>

              <p className="text-base whitespace-pre-wrap leading-relaxed text-black">
                {renderContent(msg.content)}
              </p>

              {/* 🔥 YOUR CUSTOM BLUE BUTTONS 🔥 */}
              {options && Array.isArray(options) && (
                <div className="mt-4 flex flex-wrap gap-3 border-t border-gray-100 pt-3">
                  {options.map((opt: { label: string; value: string }, btnIdx: number) => (
                    <button
                      key={`${idx}-btn-${btnIdx}`}
                      // When clicked, send the 'value' (e.g., "1" or "2") back to the server
                      onClick={() => chat.submit({ messages: [{ type: "human", content: opt.value }] })}
                      className="bg-blue-600 hover:bg-blue-700 text-white font-medium px-5 py-2.5 rounded-lg transition-colors shadow-sm"
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              )}

              {/* Keep this just in case you use standard tool calls later */}
              {msgAny.tool_calls?.map((tool: any, toolIdx: number) => (
                <div key={tool.id || `${idx}-tool-${toolIdx}`} className="mt-3 p-3 border border-gray-200 bg-gray-50 rounded text-black">
                  <p className="text-sm font-semibold mb-2">Agent used tool: {tool.name}</p>
                </div>
              ))}
            </div>
          );
        })}

        {/* Loading Indicator */}
        {chat.isLoading && (
          <div className="text-gray-500 animate-pulse bg-white border border-gray-200 p-4 rounded-xl max-w-[50%]">
            Agent is typing...
          </div>
        )}
      </div>

      {/* --- INPUT AREA --- */}
      <form onSubmit={handleSend} className="flex gap-3 pt-2 border-t border-gray-300 mt-2">
        <input
          name="message"
          type="text"
          placeholder="Type your message here..."
          className="flex-1 p-4 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-black bg-white placeholder-gray-400"
          disabled={chat.isLoading}
        />
        <button
          type="submit"
          disabled={chat.isLoading}
          className="bg-blue-600 text-white px-8 py-4 rounded-xl font-bold hover:bg-blue-700 disabled:bg-blue-300 transition-colors shadow-sm"
        >
          Send
        </button>
      </form>
    </div>
  );
}
