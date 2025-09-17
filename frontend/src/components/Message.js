import React from 'react';
import PropTypes from 'prop-types';

const MESSAGE_STYLES = {
  success: 'bg-green-700 text-green-100',
  error: 'bg-red-700 text-red-100',
  info: 'bg-blue-700 text-blue-100',
  warning: 'bg-yellow-600 text-yellow-100',
};

const Message = ({ type, text }) => {
  if (!text) {
    return null;
  }

  const resolvedType = MESSAGE_STYLES[type] ? type : 'info';
  return <div className={`p-4 rounded-md mt-4 text-sm ${MESSAGE_STYLES[resolvedType]}`}>{text}</div>;
};

Message.propTypes = {
  type: PropTypes.oneOf(Object.keys(MESSAGE_STYLES)),
  text: PropTypes.string,
};

Message.defaultProps = {
  type: 'info',
  text: undefined,
};

export default Message;
