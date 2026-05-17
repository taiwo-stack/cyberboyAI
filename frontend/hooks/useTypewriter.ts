"use client";
import { useEffect, useState } from "react";

/**
 * Simulates a terminal typewriter effect on a given string.
 * Returns the progressively revealed text and whether typing is done.
 */
export function useTypewriter(text: string, speed = 12): { displayed: string; done: boolean } {
  const [displayed, setDisplayed] = useState("");
  const [done, setDone] = useState(false);

  useEffect(() => {
    setDisplayed("");
    setDone(false);

    if (!text) {
      setDone(true);
      return;
    }

    let i = 0;
    // Adaptive speed: for long text (>400 chars), run faster to avoid user fatigue
    const ms = text.length > 400 ? Math.max(4, speed / 3) : speed;

    const timer = setInterval(() => {
      i++;
      setDisplayed(text.slice(0, i));
      if (i >= text.length) {
        clearInterval(timer);
        setDone(true);
      }
    }, ms);

    return () => clearInterval(timer);
  }, [text, speed]);

  return { displayed, done };
}
