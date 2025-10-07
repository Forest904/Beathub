import React from 'react';
import PropTypes from 'prop-types';

const MESSAGE_STYLES = {
  success: 'bg-brandSuccess-100 text-brandSuccess-800 dark:bg-brandSuccess-700 dark:text-brandSuccess-100',
  error: 'bg-brandError-100 text-brandError-800 dark:bg-brandError-700 dark:text-brandError-100',
  info: 'bg-brand-100 text-brand-800 dark:bg-brandDark-700 dark:text-brandDark-100',
  warning: 'bg-brandWarning-100 text-brandWarning-800 dark:bg-brandWarning-600 dark:text-brandWarning-100',
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
