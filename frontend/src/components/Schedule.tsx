import React, { useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import DayCard from "./DayCard";

interface ScheduleProps {
  onDateSelect?: (date: Date) => void;
}

const getWeekDates = (baseDate: Date) => {
  const baseDay = baseDate.getDay();
  const diffToMonday = baseDay === 0 ? -6 : 1 - baseDay;

  const startOfWeek = new Date(baseDate);
  startOfWeek.setDate(baseDate.getDate() + diffToMonday);

  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(startOfWeek);
    d.setDate(startOfWeek.getDate() + i);
    return d;
  });
};

const Schedule: React.FC<ScheduleProps> = ({ onDateSelect }) => {
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [weekOffset, setWeekOffset] = useState(0);
  const [direction, setDirection] = useState(0);

  const weekDates = getWeekDates(new Date(new Date().setDate(new Date().getDate() + weekOffset * 7)));

  const handleDateSelect = (date: Date) => {
    setSelectedDate(date);
    onDateSelect?.(date);
  };

  const formatDay = (date: Date) => {
    const days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
    return days[date.getDay()];
  };

  // Animation variants
  const variants = {
    enter: (dir: number) => ({
      x: dir > 0 ? 300 : -300,
      opacity: 0,
      position: "absolute" as "absolute",
    }),
    center: {
      x: 0,
      opacity: 1,
      position: "static" as "static",
    },
    exit: (dir: number) => ({
      x: dir > 0 ? -300 : 300,
      opacity: 0,
      position: "absolute" as "absolute",
    }),
  };

  const handleWeekChange = (offsetChange: number) => {
    setDirection(offsetChange);
    setWeekOffset((prev) => prev + offsetChange);
  };

  return (
    <div className="w-full bg-white p-4 rounded-xl shadow-sm overflow-hidden relative">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-gray-800 text-lg font-medium">Your Schedule</h2>
        <div className="flex space-x-2">
          <button
            onClick={() => handleWeekChange(-1)}
            className="p-1.5 bg-gray-100 text-gray-600 rounded-full hover:bg-gray-200 transition-colors"
          >
            <ChevronLeft size={16} />
          </button>
          <button
            onClick={() => handleWeekChange(1)}
            className="p-1.5 bg-gray-100 text-gray-600 rounded-full hover:bg-gray-200 transition-colors"
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </div>
      <div className="relative min-h-[72px]">
        {" "}
        {/* Set min height for smoother animation */}
        <AnimatePresence initial={false} custom={direction}>
          <motion.div
            key={weekOffset}
            className="flex space-x-2"
            custom={direction}
            variants={variants}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{ type: "spring", stiffness: 400, damping: 35 }}
          >
            {weekDates.map((date, idx) => (
              <DayCard
                key={date.toISOString()}
                day={formatDay(date)}
                date={date.getDate()}
                isSelected={date.toDateString() === selectedDate.toDateString()}
                onClick={() => handleDateSelect(date)}
              />
            ))}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
};

export default Schedule;
