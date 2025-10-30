import React from "react";

const StatusMessage = ({ status }) => {
  if (!status || status.type === "pending") {
    return status?.type === "pending" ? (
      <p className="text-xs text-slate-400 dark:text-slate-500">Working on it...</p>
    ) : null;
  }
  if (status.type === "success") {
    return <p className="text-xs font-medium text-emerald-500">{status.message}</p>;
  }
  if (status.type === "error") {
    return <p className="text-xs font-medium text-rose-500">{status.message}</p>;
  }
  return null;
};

export default StatusMessage;
