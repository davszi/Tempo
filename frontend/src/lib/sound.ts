import { appPref } from "./appPrefs.ts";
import { isMobileApp } from "./platform.ts";
import type { Grade } from "./practiceApi.ts";

/**
 * Short sounds for Repeating in the Android app, made with the Web Audio API so no audio files ship.
 * Silent on the website and when the player turns sounds off in Settings.
 */
type Tone = { freq: number; at: number; length: number; type?: OscillatorType; volume?: number; slideTo?: number };

/** The notes of each sound: start time and length in seconds. Exported for the tests. */
export const SOUNDS = {
  move: [{ freq: 520, at: 0, length: 0.07, type: "triangle", volume: 0.35, slideTo: 380 }],
  mistake: [
    { freq: 196, at: 0, length: 0.13, type: "sawtooth", volume: 0.12 },
    { freq: 147, at: 0.14, length: 0.18, type: "sawtooth", volume: 0.12 },
  ],
  swipe: [{ freq: 300, at: 0, length: 0.16, type: "sine", volume: 0.18, slideTo: 900 }],
  savedGood: [
    { freq: 523.25, at: 0, length: 0.16, volume: 0.25 },
    { freq: 659.25, at: 0.09, length: 0.16, volume: 0.25 },
    { freq: 783.99, at: 0.18, length: 0.34, volume: 0.25 },
  ],
  savedEasy: [
    { freq: 523.25, at: 0, length: 0.14, volume: 0.25 },
    { freq: 659.25, at: 0.08, length: 0.14, volume: 0.25 },
    { freq: 783.99, at: 0.16, length: 0.14, volume: 0.25 },
    { freq: 1046.5, at: 0.24, length: 0.4, volume: 0.25 },
  ],
  savedHard: [
    { freq: 440, at: 0, length: 0.18, volume: 0.22 },
    { freq: 523.25, at: 0.12, length: 0.3, volume: 0.22 },
  ],
  savedAgain: [
    { freq: 392, at: 0, length: 0.18, volume: 0.22 },
    { freq: 311.13, at: 0.14, length: 0.36, volume: 0.22 },
  ],
} satisfies Record<string, Tone[]>;
export type SoundName = keyof typeof SOUNDS;

export const savedSound = (grade: Grade): SoundName =>
  grade === "Easy" ? "savedEasy" : grade === "Good" ? "savedGood" : grade === "Hard" ? "savedHard" : "savedAgain";

let context: AudioContext | null = null;

export function playSound(name: SoundName) {
  if (!isMobileApp() || !appPref("sounds")) return;
  try {
    const Context = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!Context) return;
    context ??= new Context();
    if (context.state === "suspended") void context.resume();
    const start = context.currentTime + 0.01;
    for (const tone of SOUNDS[name] as Tone[]) {
      const oscillator = context.createOscillator();
      const gain = context.createGain();
      oscillator.type = tone.type ?? "sine";
      oscillator.frequency.setValueAtTime(tone.freq, start + tone.at);
      if (tone.slideTo) oscillator.frequency.exponentialRampToValueAtTime(tone.slideTo, start + tone.at + tone.length);
      gain.gain.setValueAtTime(0.0001, start + tone.at);
      gain.gain.exponentialRampToValueAtTime(tone.volume ?? 0.2, start + tone.at + 0.01);
      gain.gain.exponentialRampToValueAtTime(0.0001, start + tone.at + tone.length);
      oscillator.connect(gain).connect(context.destination);
      oscillator.start(start + tone.at);
      oscillator.stop(start + tone.at + tone.length + 0.02);
    }
  } catch { /* audio unavailable: stay silent */ }
}
