"use client";

/**
 * Module overview for frontend/components/VoiceInputButton.tsx.
 * Implements user-facing UI behavior for this route or component.
 */

import { useState } from "react";

type SpeechCtor = new () => {
  lang: string;
  interimResults: boolean;
  maxAlternatives: number;
  onresult: ((event: any) => void) | null;
  onerror: ((event: any) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
};

export function VoiceInputButton({ onTranscript }: { onTranscript: (text: string) => void }) {
  const [listening, setListening] = useState(false);

  return (
    <button
      className={`inline-flex h-8 w-8 items-center justify-center rounded-full text-sm text-white ${listening ? "bg-rose-600" : "bg-slate-700"}`}
      onClick={() => {
        const Ctor = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
        if (!Ctor) {
          onTranscript("Voice input is not supported in this browser.");
          return;
        }
        const recognition = new (Ctor as SpeechCtor)();
        recognition.lang = "en-US";
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;
        setListening(true);
        recognition.onresult = (event) => {
          const text = event.results?.[0]?.[0]?.transcript;
          if (text) onTranscript(text);
        };
        recognition.onerror = () => setListening(false);
        recognition.onend = () => setListening(false);
        recognition.start();
      }}
      type="button"
      aria-label="Voice prompt"
      title="Voice prompt"
    >
      {listening ? "◉" : "🎤"}
    </button>
  );
}
