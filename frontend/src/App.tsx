import { useState, useEffect } from 'react'
import AlarmList from './components/AlarmList'
import CreateAlarmButton from './components/CreateAlarmButton'
import CreateAlarmModal from './components/CreateAlarmModal'
import type { Alarm } from './types'

function App() {
  const [alarms, setAlarms] = useState<Alarm[]>([])
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  // Dummy data for development - replace with actual API call
  useEffect(() => {
    setTimeout(() => {
      setAlarms([
        {
          alarm_id: '1',
          time: '07:30',
          wake_up_sound_id: 'wake_up_sounds/wake-up-focus',
          get_up_sound_id: 'get_up_sounds/get-up-blossom',
          volume: 0.7,
          max_brightness: 80,
          wake_up_timer_duration: 300,
        },
        {
          alarm_id: '2',
          time: '08:45',
          wake_up_sound_id: 'wake_up_sounds/wake-up-energy',
          get_up_sound_id: 'get_up_sounds/get-up-chimes',
          volume: 0.5,
          max_brightness: 100,
          wake_up_timer_duration: 480,
        },
      ])
      setIsLoading(false)
    }, 1000)
  }, [])

  const handleCreateAlarm = (newAlarm: Alarm) => {
    setAlarms([...alarms, newAlarm])
    setIsModalOpen(false)
  }

  const handleDeleteAlarm = (alarmId: string) => {
    setAlarms(alarms.filter(alarm => alarm.alarm_id !== alarmId))
  }

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900 p-4 md:p-6">
      <header className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800 dark:text-white">
          Jarvis Alarm System
        </h1>
        <p className="text-gray-600 dark:text-gray-300">
          Manage your smart alarms
        </p>
      </header>

      <AlarmList 
        alarms={alarms} 
        isLoading={isLoading} 
        onDelete={handleDeleteAlarm} 
      />

      <CreateAlarmButton onClick={() => setIsModalOpen(true)} />

      {isModalOpen && (
        <CreateAlarmModal
          onClose={() => setIsModalOpen(false)}
          onSave={handleCreateAlarm}
        />
      )}
    </div>
  )
}

export default App
