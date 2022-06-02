import React from 'react';

import { Text } from 'components/kit';
import ErrorBoundary from 'components/ErrorBoundary/ErrorBoundary';

import stopPropagation from 'utils/stopPropagation';

import { IStatusLabelProps } from './types.d';

import './styles.scss';

/**
 * @property {string} title - label title
 * @property {string} status - status type
 * @property {string} className - component className
 */
function StatusLabel({
  title,
  status = 'success',
  className = '',
}: IStatusLabelProps): React.FunctionComponentElement<React.ReactNode> {
  return (
    <ErrorBoundary>
      <div
        onClick={stopPropagation}
        className={`StatusLabel ${status} ${className}`}
      >
        {title && (
          <Text size={10} weight={600} className='StatusLabel__title title'>
            {title}
          </Text>
        )}
      </div>
    </ErrorBoundary>
  );
}

StatusLabel.displayName = 'StatusLabel';

export default React.memo<IStatusLabelProps>(StatusLabel);
