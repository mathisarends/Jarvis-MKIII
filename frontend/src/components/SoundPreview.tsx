import { useState, useRef, useEffect } from 'react';
import { getSoundUrl } from '../api/alarmApi';

interface SoundPreviewProps {
  soundId: string;
  volume: number;
}

const SoundPreview = ({ soundId, volume }: SoundPreviewProps) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    if (!audioRef.current) {
      audioRef.current = new Audio();
    }
    
    // Update volume when prop changes
    if (audioRef.current) {
      audioRef.current.volume = volume;
    }
    
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
    };
  }, [volume]);

  const handlePlayPreview = () => {
    if (!audioRef.current) return;
    
    if (isPlaying) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      setIsPlaying(false);
      return;
    }
    
    const soundUrl = getSoundUrl(soundId);
    audioRef.current.src = soundUrl;
    audioRef.current.volume = volume;
    
    audioRef.current.onended = () => {
      setIsPlaying(false);
    };
    
    audioRef.current.oncanplaythrough = () => {
      audioRef.current?.play();
    };
    
    audioRef.current.onerror = (e) => {
      console.error('Error playing audio:', e);
      setIsPlaying(false);
    };
    
    setIsPlaying(true);
    audioRef.current.load();
  };

  return (
    <button
      onClick={handlePlayPreview}
      className="p-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
      aria-label={isPlaying ? 'Stop preview' : 'Play preview'}
    >
      {isPlaying ? (
        <svg
          className="w-5 h-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      ) : (
        <svg
          className="w-5 h-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
          />
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      )}
    </button>
  );
};

export default SoundPreview; 