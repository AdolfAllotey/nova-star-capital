import React, { useState } from "react";

export function Tabs({ tabs, defaultTab, className }) {
  const [activeTab, setActiveTab] = useState(defaultTab || tabs[0].id);

  return (
    <div className={className}>
      <div className="flex space-x-4 border-b border-neutral-200 dark:border-neutral-700 mb-4">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            className={`px-4 py-2 text-sm font-medium ${
              activeTab === tab.id
                ? "border-b-2 border-blue-500 text-blue-600 dark:text-blue-400"
                : "text-neutral-600 dark:text-neutral-400 hover:text-neutral-800 dark:hover:text-neutral-200"
            }`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div>
        {tabs.map((tab) =>
          tab.id === activeTab ? (
            <div key={tab.id} className="pt-2">
              {tab.content}
            </div>
          ) : null
        )}
      </div>
    </div>
  );
}