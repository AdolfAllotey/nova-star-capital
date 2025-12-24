import React from "react";

const SignalSummary = ({ signals }) => {
  if (!signals || signals.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-900 p-4 rounded-2xl shadow-md">
        <p className="text-gray-600 dark:text-gray-300 text-sm">
          Aucun signal détecté pour le moment.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-900 p-4 rounded-2xl shadow-md">
      <h2 className="text-lg font-semibold text-gray-800 dark:text-white mb-4">
        Résumé des signaux détectés
      </h2>
      <ul className="space-y-2">
        {signals.map((signal, index) => (
          <li
            key={index}
            className="border border-gray-200 dark:border-gray-700 rounded-xl p-3 hover:bg-gray-50 dark:hover:bg-gray-800 transition"
          >
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium text-gray-900 dark:text-white">
                {signal.token}
              </span>
              <span className="text-sm text-gray-500 dark:text-gray-400">
                {signal.source}
              </span>
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">
              {signal.description}
            </p>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default SignalSummary;