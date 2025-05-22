import React, { createContext, useContext, useCallback, useState } from "react";
import { soundApi } from "../api/alarmApi";

interface SoundPlaybackContextType {
  currentlyPlaying: string | null;
  setCurrentlyPlaying: (soundId: string | null) => void;
  stopAllSounds: () => Promise<void>;
}

const SoundPlaybackContext = createContext<SoundPlaybackContextType | null>(null);

export const SoundPlaybackProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentlyPlaying, setCurrentlyPlayingState] = useState<string | null>(null);

  const setCurrentlyPlaying = useCallback((soundId: string | null) => {
    setCurrentlyPlayingState(soundId);
  }, []);

  const stopAllSounds = useCallback(async () => {
    try {
      await soundApi.stop();
      setCurrentlyPlayingState(null);
    } catch (error) {
      console.error("Error stopping all sounds:", error);
    }
  }, []);

  return (
    <SoundPlaybackContext.Provider value={{ currentlyPlaying, setCurrentlyPlaying, stopAllSounds }}>
      {children}
    </SoundPlaybackContext.Provider>
  );
};

export const useSoundPlayback = () => {
  const context = useContext(SoundPlaybackContext);
  if (!context) {
    throw new Error("useSoundPlayback must be used within SoundPlaybackProvider");
  }
  return context;
};

export type { SoundPlaybackContextType };
