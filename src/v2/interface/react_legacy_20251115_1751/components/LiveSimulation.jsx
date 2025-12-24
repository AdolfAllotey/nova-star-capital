import React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { LiveSimulationChart } from "./LiveSimulationChart";

const LiveSimulation = () => {
  return (
    <Card className="w-full shadow-md rounded-2xl mb-6">
      <CardContent className="p-4">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">📈 Simulation en direct</h2>
        </div>
        <LiveSimulationChart />
      </CardContent>
    </Card>
  );
};

export { LiveSimulation };