import React, { useState, useEffect } from "react";
import { Bell, ChevronUp } from "lucide-react";

interface AlarmOverlayProps {
  isVisible: boolean;
  alarmTime: string;
  currentTime?: string;
  userName?: string;
  onDismiss: () => void;
  onSnooze?: () => void;
}

const AlarmOverlay: React.FC<AlarmOverlayProps> = ({
  isVisible,
  alarmTime,
  currentTime,
  userName = "User",
  onDismiss,
  onSnooze,
}) => {
  const [time, setTime] = useState(
    currentTime ||
      new Date().toLocaleTimeString("de-DE", {
        hour: "2-digit",
        minute: "2-digit",
      })
  );
  const [swipeOffset, setSwipeOffset] = useState(0);
  const [isDragging, setIsDragging] = useState(false);

  // Update time every second
  useEffect(() => {
    if (!isVisible) {
      return;
    }

    const interval = setInterval(() => {
      setTime(
        new Date().toLocaleTimeString("de-DE", {
          hour: "2-digit",
          minute: "2-digit",
        })
      );
    }, 1000);

    return () => clearInterval(interval);
  }, [isVisible]);

  // Handle swipe gesture
  const handleTouchStart = (e: React.TouchEvent) => {
    setIsDragging(true);
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    if (!isDragging) return;

    const touch = e.touches[0];
    const startY = window.innerHeight - 200; // Approximate button position
    const currentY = touch.clientY;
    const offset = Math.max(0, startY - currentY);

    setSwipeOffset(Math.min(offset, 100));
  };

  const handleTouchEnd = () => {
    if (swipeOffset > 50) {
      onDismiss();
    } else {
      setSwipeOffset(0);
    }
    setIsDragging(false);
  };

  if (!isVisible) return null;

  return (
    <div
      className="fixed inset-0 z-50 bg-gradient-to-b from-slate-900 via-slate-800 to-slate-900 
                    flex flex-col items-center justify-between text-white overflow-hidden"
    >
      {/* Animated stars background */}
      <div className="absolute inset-0 overflow-hidden">
        {[...Array(50)].map((_, i) => (
          <div
            key={i}
            className="absolute w-1 h-1 bg-white rounded-full animate-pulse"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              animationDelay: `${Math.random() * 3}s`,
              animationDuration: `${2 + Math.random() * 2}s`,
            }}
          />
        ))}
      </div>

      {/* Top section */}
      <div className="flex flex-col items-center pt-16 px-6 z-10">
        {/* Alarm badge */}
        <div
          className="flex items-center gap-2 mb-4 bg-black/30 px-3 py-1 rounded-full 
                       backdrop-blur-sm border border-white/20"
        >
          <Bell className="w-4 h-4" />
          <span className="text-sm font-medium">ALARM AT {alarmTime}</span>
        </div>

        {/* Greeting */}
        <h1 className="text-2xl font-light mb-8 text-center opacity-90">Good Night, {userName}!</h1>

        {/* Current time */}
        <div className="text-7xl font-extralight tracking-wider mb-12">{time}</div>
      </div>

      {/* Moon illustration */}
      <div className="flex-1 flex items-center justify-center relative">
        <div className="relative">
          {/* Moon */}
          <div
            className="w-32 h-32 bg-gradient-to-br from-gray-200 to-gray-300 rounded-full 
                         relative shadow-2xl"
          >
            {/* Moon craters */}
            <div className="absolute top-6 left-8 w-3 h-3 bg-gray-400 rounded-full opacity-40"></div>
            <div className="absolute top-12 right-6 w-2 h-2 bg-gray-400 rounded-full opacity-30"></div>
            <div className="absolute bottom-8 left-12 w-4 h-4 bg-gray-400 rounded-full opacity-35"></div>
          </div>

          {/* Clouds */}
          <div
            className="absolute -bottom-4 -left-12 w-20 h-8 bg-gradient-to-r from-gray-600 to-gray-500 
                         rounded-full opacity-60"
          ></div>
          <div
            className="absolute -bottom-2 right-8 w-16 h-6 bg-gradient-to-r from-gray-500 to-gray-600 
                         rounded-full opacity-50"
          ></div>
          <div
            className="absolute top-4 -right-8 w-12 h-5 bg-gradient-to-r from-gray-600 to-gray-500 
                         rounded-full opacity-40"
          ></div>

          {/* Twinkling stars around moon */}
          <div className="absolute -top-8 -right-4 w-1 h-1 bg-white rounded-full animate-ping"></div>
          <div
            className="absolute top-16 -left-8 w-1 h-1 bg-white rounded-full animate-ping 
                         animation-delay-1000"
          ></div>
          <div
            className="absolute -bottom-12 right-4 w-1 h-1 bg-white rounded-full animate-ping 
                         animation-delay-2000"
          ></div>
        </div>
      </div>

      {/* Sleep duration */}
      <div className="mb-8 text-center z-10">
        <p className="text-sm text-gray-400 mb-2">Sleep Duration</p>
        <div className="bg-blue-600 px-4 py-2 rounded-lg">
          <span className="text-white font-medium">8h 25m</span>
        </div>
      </div>

      {/* Swipe to wake up */}
      <div className="pb-12 px-6 w-full z-10">
        <div
          className="relative bg-white/20 backdrop-blur-sm rounded-full h-16 flex items-center 
                     justify-center border border-white/30 cursor-pointer transition-all duration-300"
          onTouchStart={handleTouchStart}
          onTouchMove={handleTouchMove}
          onTouchEnd={handleTouchEnd}
          style={{
            transform: `translateY(-${swipeOffset}px)`,
            opacity: 1 - swipeOffset / 200,
          }}
        >
          {/* Swipe indicator */}
          <div className="flex flex-col items-center gap-1 text-white/90">
            <ChevronUp className="w-6 h-6" />
            <span className="text-sm font-medium">Swipe to wake up</span>
          </div>

          {/* Animated arrow */}
          <div className="absolute top-2 left-1/2 transform -translate-x-1/2">
            <ChevronUp className="w-4 h-4 text-white/50 animate-bounce" />
          </div>
        </div>

        {/* Snooze option */}
        {onSnooze && (
          <button
            onClick={onSnooze}
            className="w-full mt-4 py-3 text-center text-white/70 text-sm hover:text-white/90 
                       transition-colors"
          >
            Snooze 9 minutes
          </button>
        )}
      </div>

      {/* Subtle gradient overlay for depth */}
      <div
        className="absolute inset-0 bg-gradient-to-t from-black/20 via-transparent to-black/10 
                     pointer-events-none"
      ></div>
    </div>
  );
};

// Demo component to test the overlay
const AlarmOverlayDemo: React.FC = () => {
  const [showOverlay, setShowOverlay] = useState(false);

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
      <div className="text-center">
        <h2 className="text-2xl font-bold mb-4">Alarm Overlay Demo</h2>
        <button
          onClick={() => setShowOverlay(true)}
          className="bg-blue-500 text-white px-6 py-3 rounded-lg hover:bg-blue-600 transition-colors"
        >
          Show Alarm Overlay
        </button>
      </div>

      <AlarmOverlay
        isVisible={showOverlay}
        alarmTime="06:15 AM"
        userName="Mathis"
        onDismiss={() => {
          setShowOverlay(false);
          alert("Alarm dismissed! Good morning! ☀️");
        }}
        onSnooze={() => {
          setShowOverlay(false);
          alert("Snoozed for 9 minutes! 😴");
        }}
      />
    </div>
  );
};

export default AlarmOverlayDemo;
