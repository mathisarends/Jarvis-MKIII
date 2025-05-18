import type { Alarm } from '../types'
import AlarmCard from './AlarmCard'

interface AlarmListProps {
  alarms: Alarm[]
  isLoading: boolean
  onDelete: (alarmId: string) => void
}

const AlarmList = ({ alarms, isLoading, onDelete }: AlarmListProps) => {
  if (isLoading) {
    return (
      <div className="flex justify-center items-center p-8">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    )
  }

  if (alarms.length === 0) {
    return (
      <div className="card p-6 flex flex-col items-center justify-center">
        <svg
          className="w-16 h-16 text-gray-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M12 6v6m0 0v6m0-6h6m-6 0H6"
          />
        </svg>
        <h3 className="mt-4 font-semibold text-gray-700 dark:text-gray-200">
          No Alarms Set
        </h3>
        <p className="mt-2 text-gray-500 dark:text-gray-400 text-center">
          Add a new alarm using the button in the bottom right corner.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {alarms.map((alarm) => (
        <AlarmCard key={alarm.alarm_id} alarm={alarm} onDelete={onDelete} />
      ))}
    </div>
  )
}

export default AlarmList 