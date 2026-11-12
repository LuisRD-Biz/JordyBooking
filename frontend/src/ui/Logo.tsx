import React from 'react';

/** The studio's monogram: "JF" in the brand typeface, crema on espresso with a calabaza rule. */
export function Logo({size, pulse = false}: {size?: 'small' | 'large'; pulse?: boolean}) {
  return <span className={['brand-symbol', size, pulse && 'pulse'].filter(Boolean).join(' ')} aria-hidden="true"><span>JF</span></span>;
}
