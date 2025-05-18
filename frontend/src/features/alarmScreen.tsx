import React from "react";
import Schedule from "../components/Schedule";

const ScheduleDemo: React.FC = () => {
  const handleDateSelect = (date: Date) => {
    console.log("Selected date:", date.toDateString());
    // Hier könntest du Termindetails für das ausgewählte Datum laden
  };

  return <Schedule onDateSelect={handleDateSelect} />;
};

export default ScheduleDemo;
