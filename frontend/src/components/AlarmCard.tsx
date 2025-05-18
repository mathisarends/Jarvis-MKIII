import type { Alarm } from '../types'

interface AlarmCardProps {
  alarm: Alarm
  onDelete: (alarmId: string) => void
}

const AlarmCard = ({ alarm, onDelete }: AlarmCardProps) => {
  const formattedTime = alarm.time
  const wakeSoundName = alarm.wake_up_sound_id.split('/').pop() || ''
  const getUpSoundName = alarm.get_up_sound_id.split('/').pop() || ''
  
  return (
    <div className="card">
      <div className="p-4">
        <div className="flex justify-between items-center">
          <h2 className="text-xl font-bold text-gray-800 dark:text-white">
            {formattedTime}
          </h2>
          <button
            className="text-red-500 hover:text-red-700 dark:hover:text-red-400 p-1"
            onClick={() => onDelete(alarm.alarm_id)}
            aria-label="Delete alarm"
          >
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
                strokeWidth={1.5}
                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
              />
            </svg>
          </button>
        </div>

        <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
          <div className="text-gray-500 dark:text-gray-400">Wake-up Sound:</div>
          <div className="text-gray-700 dark:text-gray-300">{wakeSoundName}</div>
          
          <div className="text-gray-500 dark:text-gray-400">Get-up Sound:</div>
          <div className="text-gray-700 dark:text-gray-300">{getUpSoundName}</div>
          
          <div className="text-gray-500 dark:text-gray-400">Volume:</div>
          <div className="text-gray-700 dark:text-gray-300">{(alarm.volume * 100).toFixed(0)}%</div>
          
          <div className="text-gray-500 dark:text-gray-400">Brightness:</div>
          <div className="text-gray-700 dark:text-gray-300">{alarm.max_brightness}%</div>
          
          <div className="text-gray-500 dark:text-gray-400">Duration:</div>
          <div className="text-gray-700 dark:text-gray-300">{Math.floor(alarm.wake_up_timer_duration / 60)}m {alarm.wake_up_timer_duration % 60}s</div>
        </div>
      </div>
    </div>
  )
}

export default AlarmCard 