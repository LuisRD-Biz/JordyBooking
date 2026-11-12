import React from 'react';

export function Logo({size, pulse = false}: {size?: 'small' | 'large'; pulse?: boolean}) {
  return <span className={['brand-symbol', size, pulse && 'pulse'].filter(Boolean).join(' ')} aria-hidden="true"><span>JF</span></span>;
}
