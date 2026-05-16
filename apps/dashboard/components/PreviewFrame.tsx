"use client";

import { useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

type DeviceSize = "desktop" | "tablet" | "mobile";

const DEVICE_WIDTHS: Record<DeviceSize, number> = {
  desktop: 1440,
  tablet: 768,
  mobile: 375,
};

const DEVICE_LABELS: Record<DeviceSize, string> = {
  desktop: "Desktop",
  tablet: "Tablet",
  mobile: "Mobile",
};

interface PreviewFrameProps {
  previewUrl: string;
  title?: string;
}

export default function PreviewFrame({
  previewUrl,
  title = "Preview",
}: PreviewFrameProps) {
  const [device, setDevice] = useState<DeviceSize>("desktop");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const isValidUrl = (() => {
    try {
      new URL(previewUrl);
      return true;
    } catch {
      return false;
    }
  })();

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle>{title}</CardTitle>
        <div className="flex items-center gap-2">
          <div className="flex rounded-md border">
            {(Object.keys(DEVICE_WIDTHS) as DeviceSize[]).map((d) => (
              <Button
                key={d}
                variant={device === d ? "default" : "ghost"}
                size="sm"
                className="rounded-none first:rounded-l-md last:rounded-r-md text-xs"
                onClick={() => setDevice(d)}
              >
                {DEVICE_LABELS[d]}
              </Button>
            ))}
          </div>
          {isValidUrl && (
            <Button variant="outline" size="sm" asChild>
              <a href={previewUrl} target="_blank" rel="noopener noreferrer">
                Open in New Tab
              </a>
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {!isValidUrl ? (
          <div className="flex h-96 items-center justify-center rounded-md bg-muted">
            <div className="text-center">
              <p className="text-lg font-medium text-muted-foreground">
                Invalid Preview URL
              </p>
              <p className="mt-1 text-sm text-muted-foreground">
                The preview URL is not available or incorrectly formatted.
              </p>
            </div>
          </div>
        ) : (
          <div className="flex justify-center overflow-hidden rounded-md bg-muted">
            <div
              style={{ width: DEVICE_WIDTHS[device] }}
              className="relative max-w-full transition-all duration-300"
            >
              {loading && (
                <div className="absolute inset-0 flex items-center justify-center bg-muted">
                  <div className="flex flex-col items-center gap-2">
                    <svg
                      className="h-8 w-8 animate-spin text-muted-foreground"
                      viewBox="0 0 24 24"
                      fill="none"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                      />
                    </svg>
                    <span className="text-sm text-muted-foreground">
                      Loading preview...
                    </span>
                  </div>
                </div>
              )}
              {error && (
                <div className="absolute inset-0 flex items-center justify-center bg-muted">
                  <div className="text-center">
                    <p className="text-lg font-medium text-destructive">
                      Failed to Load
                    </p>
                    <p className="mt-1 text-sm text-muted-foreground">
                      The preview could not be loaded. Try refreshing or opening
                      in a new tab.
                    </p>
                  </div>
                </div>
              )}
              <iframe
                src={previewUrl}
                title="Preview"
                className="h-[600px] w-full border-0 bg-white"
                sandbox="allow-scripts allow-same-origin"
                onLoad={() => setLoading(false)}
                onError={() => {
                  setLoading(false);
                  setError(true);
                }}
              />
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}