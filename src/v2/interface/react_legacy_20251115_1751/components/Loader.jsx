import React from "react";

const Loader = ({ message = "Chargement en cours..." }) => {
  return (
    <div className="flex flex-col items-center justify-center h-40 text-center text-gray-600 dark:text-gray-300">
      <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500 mb-2"></div>
      <p className="text-sm">{message}</p>
    </div>
  );
};

export default Loader;