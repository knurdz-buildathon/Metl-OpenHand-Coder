"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface LogEntry {
  timestamp: string;
  level: "info" | "warn" | "error" | "debug" | "success";
  message: string;
}

const LEVEL_COLORS: Record<string, string> = {
  info: "text-blue-400",
  warn: "text-yellow-400",
  error: "text-red-400",
  debug: "text-gray-400",
  success: "text-green-400",
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api";
const WS_BASE = typeof window !== "undefined" 
  ? `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}${API_BASE}`
  : API_BASE.replace(/^http/, "ws");

interface LogStreamProps {
  jobId: string;
}

export default function LogStream({ jobId }: LogStreamProps) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [expanded, setExpanded] = useState(true);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const logEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout>>();

  const scrollToBottom = useCallback(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      const ws = new WebSocket(`${WS_BASE}/v1/jobs/${jobId}/logs`);

      ws.onopen = () => {
        setConnected(true);
        setError(null);
      };

      ws.onmessage = (event) => {
        try {
          const entry: LogEntry = JSON.parse(event.data);
          setLogs((prev) => [...prev, entry]);
        } catch {
          setLogs((prev) => [
            ...prev,
            {
              timestamp: new Date().toISOString(),
              level: "info",
              message: event.data,
            },
          ]);
        }
      };

      ws.onclose = () => {
        setConnected(false);
        reconnectTimeoutRef.current = setTimeout(connect, 3000);
      };

      ws.onerror = () => {
        setError("WebSocket connection error");
        ws.close();
      };

      wsRef.current = ws;
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to connect to log stream"
      );
    }
  }, [jobId]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeoutRef.current)
        clearTimeout(reconnectTimeoutRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  useEffect(() => {
    if (expanded) scrollToBottom();
  }, [logs, expanded, scrollToBottom]);

  const handleClear = () => setLogs([]);

  const formatTimestamp = (ts: string): string => {
    const d = new Date(ts);
    return d.toLocaleTimeString("en-US", {
      hour12: false,
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="flex items-center gap-2">
          Logs
          <span
            className={`inline-block h-2 w-2 rounded-full ${
              connected ? "bg-green-500" : "bg-red-500"
            }`}
          />
        </CardTitle>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? "Collapse" : "Expand"}
          </Button>
          <Button variant="ghost" size="sm" onClick={handleClear}>
            Clear
          </Button>
        </div>
      </CardHeader>
      {expanded && (
        <CardContent>
          {error && (
            <div className="mb-2 rounded-md bg-destructive/10 p-2 text-sm text-destructive">
              {error}
            </div>
          )}
          <div className="h-64 overflow-y-auto rounded-md bg-black/90 p-4 font-mono text-xs leading-relaxed">
            {logs.length === 0 ? (
              <div className="flex h-full items-center justify-center text-gray-500">
                {connected
                  ? "Waiting for logs..."
                  : "Connecting to log stream..."}
              </div>
            ) : (
              <>
                {logs.map((entry, i) => (
                  <div key={i} className="flex gap-2">
                    <span className="shrink-0 text-gray-500 select-none">
                      {formatTimestamp(entry.timestamp)}
                    </span>
                    <span
                      className={`${LEVEL_COLORS[entry.level] || "text-gray-300"} break-all`}
                    >
                      {entry.message}
                    </span>
                  </div>
                ))}
                <div ref={logEndRef} />
              </>
            )}
          </div>
        </CardContent>
      )}
    </Card>
  );
}