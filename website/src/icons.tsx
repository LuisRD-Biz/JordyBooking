export function SocialIcon({kind}: {kind: string}) {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className="icon">
    {kind === 'Instagram' ? <><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r=".7"/></>
      : kind === 'Facebook' ? <path d="M14 22V12h4l.6-4H14V6c0-1 .4-2 2-2h3V1h-3c-4 0-6 2-6 5v2H7v4h3v10"/>
      : kind === 'Paquetes' ? <><rect x="3" y="8" width="18" height="13" rx="2"/><path d="M3 12h18M12 8v13M12 8c-1.5-4-6-4-5-1 .5 1.5 3 1 5 1Zm0 0c1.5-4 6-4 5-1-.5 1.5-3 1-5 1Z"/></>
      : <><path d="M4 18 2 22l5-1a10 10 0 1 0-3-3Z"/><path d="m8 7 2 3-1 1c1 2 2 3 4 3l1-1 3 2c-1 4-6 2-8 0S5 8 8 7Z"/></>}
  </svg>;
}

export function CameraMark() {
  return <svg viewBox="0 0 64 64" className="mark-camera" aria-hidden="true">
    <path d="M22 19l4-7h12l4 7z" fill="#3b2418"/>
    <rect x="6" y="18" width="52" height="36" rx="7" fill="#3b2418"/>
    <rect x="45" y="23" width="7" height="4" rx="2" fill="#d9772b"/>
    <circle cx="32" cy="36" r="14.5" fill="#f6ebdd"/>
    <circle cx="32" cy="36" r="14.5" fill="none" stroke="#d9772b" strokeWidth="2"/>
    <text x="31.5" y="41.5" textAnchor="middle" className="mark-initials" fontSize="16" fill="#3b2418">JF</text>
  </svg>;
}

export function PhotographerMark() {
  return <svg viewBox="0 0 120 132" className="mark-photographer" aria-hidden="true">
    <ellipse cx="60" cy="15" rx="21" ry="4" fill="#3b2418"/>
    <path d="M47 15c0-9 5-12 13-12s13 3 13 12z" fill="#3b2418"/>
    <circle cx="60" cy="26" r="12" fill="#3b2418"/>
    <path d="M41 132 36 66c0-12 5-19 13-21l5-2h12l5 2c8 2 13 9 13 21l-5 66z" fill="#3b2418"/>
    <path d="M48 46 45 132M72 46l3 86" stroke="#d9772b" strokeWidth="4.5" fill="none"/>
    <path d="M45 74h30" stroke="#d9772b" strokeWidth="3.5"/>
    <path d="M40 54 13 86 46 34M80 54l27 32-33-52" stroke="#3b2418" strokeWidth="10" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
    <path d="M52 20l2-4h8l2 4z" fill="#8b4a2b"/>
    <rect x="42" y="19" width="36" height="20" rx="4" fill="#8b4a2b"/>
    <circle cx="60" cy="29" r="7.5" fill="#3b2418" stroke="#f6ebdd" strokeWidth="2"/>
    <circle cx="57.500" cy="26.500" r="1.800" fill="#f6ebdd"/>
    <text x="60" y="98" textAnchor="middle" className="mark-initials" fontSize="17" fill="#f6ebdd">JF</text>
    <rect x="64" y="106" width="27" height="18" rx="4" fill="#8b4a2b" stroke="#f6ebdd" strokeWidth="1.5"/>
    <circle cx="77.500" cy="115" r="5.500" fill="#3b2418" stroke="#f6ebdd" strokeWidth="1.5"/>
  </svg>;
}
