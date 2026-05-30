import { useEffect, useRef, useState } from "react";

const API_BASE =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:9000";

export type IntelligenceSocketMessage = {
  type: string;
  severity?: "critical" | "risky" | "watchlist" | "stable";
  title?: string;
  description?: string;
  payload?: any;
  created_at?: string;
};

function getWebSocketUrl() {
  const baseUrl = API_BASE.replace(/\/$/, "");

  if (baseUrl.startsWith("https://")) {
    return baseUrl.replace("https://", "wss://") + "/ws/intelligence";
  }

  if (baseUrl.startsWith("http://")) {
    return baseUrl.replace("http://", "ws://") + "/ws/intelligence";
  }

  return `ws://${baseUrl}/ws/intelligence`;
}

export function useIntelligenceSocket() {
  const [connected, setConnected] = useState(false);
  const [lastMessage, setLastMessage] =
    useState<IntelligenceSocketMessage | null>(null);

  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let reconnectTimer: number | undefined;

    function connect() {
      const socket = new WebSocket(getWebSocketUrl());
      socketRef.current = socket;

      socket.onopen = () => {
        setConnected(true);
      };

      socket.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data);
          setLastMessage(parsed);
        } catch {
          setLastMessage({
            type: "raw_message",
            description: event.data,
            created_at: new Date().toISOString(),
          });
        }
      };

      socket.onclose = () => {
        setConnected(false);

        reconnectTimer = window.setTimeout(() => {
          connect();
        }, 5000);
      };

      socket.onerror = () => {
        setConnected(false);
        socket.close();
      };
    }

    connect();

    return () => {
      if (reconnectTimer) {
        window.clearTimeout(reconnectTimer);
      }

      socketRef.current?.close();
    };
  }, []);

  function sendMessage(message: IntelligenceSocketMessage) {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(message));
    }
  }

  return {
    connected,
    lastMessage,
    sendMessage,
  };
}
