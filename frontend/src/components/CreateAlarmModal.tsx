import { useState, useEffect } from 'react'
import type { Alarm, AlarmOptions } from '../types'

interface CreateAlarmModalProps {
  onClose: () => void
  onSave: (alarm: Alarm) => void
}

const CreateAlarmModal = ({ onClose, onSave }: CreateAlarmModalProps) => {
  const [time, setTime] = useState('07:30')
  const [wakeUpSoundId, setWakeUpSoundId] = useState('')
  const [getUpSoundId, setGetUpSoundId] = useState('')
  const [volume, setVolume] = useState(0.7)
  const [brightness, setBrightness] = useState(75)
  const [duration, setDuration] = useState(300)
  const [options, setOptions] = useState<AlarmOptions | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [previewingSound, setPreviewingSound] = useState<string | null>(null)

  // Load alarm options from API
  useEffect(() => {
    // In a real implementation, replace with an actual API call
    setTimeout(() => {
      setOptions({
        wake_up_sounds: [
          { id: 'wake_up_sounds/wake-up-focus', label: 'Focus' },
          { id: 'wake_up_sounds/wake-up-energy', label: 'Energy' },
          { id: 'wake_up_sounds/wake-up-calm', label: 'Calm' },
        ],
        get_up_sounds: [
          { id: 'get_up_sounds/get-up-blossom', label: 'Blossom' },
          { id: 'get_up_sounds/get-up-chimes', label: 'Chimes' },
          { id: 'get_up_sounds/get-up-sunrise', label: 'Sunrise' },
        ],
        volume_range: {
          min: 0,
          max: 1,
          default: 0.5,
        },
        brightness_range: {
          min: 0,
          max: 100,
          default: 75,
        },
      })
      setIsLoading(false)
      setWakeUpSoundId('wake_up_sounds/wake-up-focus')
      setGetUpSoundId('get_up_sounds/get-up-blossom')
    }, 800)
  }, [])

  const handleSave = () => {
    const newAlarm: Alarm = {
      alarm_id: Date.now().toString(), // Generate unique ID
      time,
      wake_up_sound_id: wakeUpSoundId,
      get_up_sound_id: getUpSoundId,
      volume,
      max_brightness: brightness,
      wake_up_timer_duration: duration,
    }
    onSave(newAlarm)
  }

  const handlePreviewSound = (soundId: string) => {
    setPreviewingSound(soundId)
    // In a real implementation, you would make an API call to play the sound
    // Example: fetch(`/api/alarms/sounds/preview?sound_id=${encodeURIComponent(soundId)}&volume=${volume}`)
    
    // Simulate ending the preview after 3 seconds
    setTimeout(() => {
      setPreviewingSound(null)
    }, 3000)
  }

  if (isLoading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center p-4 z-50">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 w-full max-w-md">
          <div className="animate-pulse flex justify-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center p-4 z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 w-full max-w-md">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold text-gray-800 dark:text-white">Create New Alarm</h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-white"
            aria-label="Close"
          >
            <svg
              className="w-6 h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <div className="space-y-4">
          {/* Time selector */}
          <div>
            <label htmlFor="time" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Alarm Time
            </label>
            <input
              type="time"
              id="time"
              value={time}
              onChange={(e) => setTime(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm dark:bg-gray-700 dark:border-gray-600 dark:text-white"
            />
          </div>

          {/* Wake-up sound selector */}
          <div>
            <label htmlFor="wake-up-sound" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Wake-up Sound
            </label>
            <div className="flex space-x-2">
              <select
                id="wake-up-sound"
                value={wakeUpSoundId}
                onChange={(e) => setWakeUpSoundId(e.target.value)}
                className="flex-grow px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              >
                {options?.wake_up_sounds.map((sound) => (
                  <option key={sound.id} value={sound.id}>
                    {sound.label}
                  </option>
                ))}
              </select>
              <button
                onClick={() => handlePreviewSound(wakeUpSoundId)}
                disabled={previewingSound !== null}
                className="p-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                aria-label="Preview wake-up sound"
              >
                {previewingSound === wakeUpSoundId ? (
                  <span className="flex items-center space-x-1">
                    <span className="animate-pulse">●</span>
                  </span>
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
            </div>
          </div>

          {/* Get-up sound selector */}
          <div>
            <label htmlFor="get-up-sound" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Get-up Sound
            </label>
            <div className="flex space-x-2">
              <select
                id="get-up-sound"
                value={getUpSoundId}
                onChange={(e) => setGetUpSoundId(e.target.value)}
                className="flex-grow px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              >
                {options?.get_up_sounds.map((sound) => (
                  <option key={sound.id} value={sound.id}>
                    {sound.label}
                  </option>
                ))}
              </select>
              <button
                onClick={() => handlePreviewSound(getUpSoundId)}
                disabled={previewingSound !== null}
                className="p-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                aria-label="Preview get-up sound"
              >
                {previewingSound === getUpSoundId ? (
                  <span className="flex items-center space-x-1">
                    <span className="animate-pulse">●</span>
                  </span>
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
            </div>
          </div>

          {/* Volume control */}
          <div>
            <label htmlFor="volume" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Volume: {Math.round(volume * 100)}%
            </label>
            <input
              type="range"
              id="volume"
              min={options?.volume_range.min || 0}
              max={options?.volume_range.max || 1}
              step="0.01"
              value={volume}
              onChange={(e) => setVolume(Number(e.target.value))}
              className="w-full"
            />
          </div>

          {/* Brightness control */}
          <div>
            <label htmlFor="brightness" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Max Brightness: {Math.round(brightness)}%
            </label>
            <input
              type="range"
              id="brightness"
              min={options?.brightness_range.min || 0}
              max={options?.brightness_range.max || 100}
              step="1"
              value={brightness}
              onChange={(e) => setBrightness(Number(e.target.value))}
              className="w-full"
            />
          </div>

          {/* Duration control */}
          <div>
            <label htmlFor="duration" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Duration between alarms: {Math.floor(duration / 60)}m {duration % 60}s
            </label>
            <input
              type="range"
              id="duration"
              min="60"
              max="900"
              step="30"
              value={duration}
              onChange={(e) => setDuration(Number(e.target.value))}
              className="w-full"
            />
          </div>
          
          <div className="flex justify-end space-x-2 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="btn btn-secondary"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSave}
              className="btn btn-primary"
            >
              Save Alarm
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default CreateAlarmModal 