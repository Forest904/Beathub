// src/components/Message.js
import React from 'react';

function Message({ type, text }) {
    if (!text) return null;

    const baseClasses = "message-box p-4 rounded-md mt-4 text-sm";
    const typeClasses = {
        success: "bg-green-700 text-green-100",
        error: "bg-red-700 text-red-100",
        info: "bg-blue-700 text-blue-100",
    };

    return (
        <div className={`${baseClasses} ${typeClasses[type]}`}>
            {text}
        </div>
    );
}

export default Message;