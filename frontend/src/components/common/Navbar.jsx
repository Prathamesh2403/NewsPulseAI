import { NavLink } from 'react-router-dom'

/* ── Static placeholder user (no auth) ─────────────────────────────── */
const user = {
  name: 'John D.',
  avatar: null,
}

/* ── Nav tabs config ───────────────────────────────────────────────── */
const navTabs = [
  { to: '/', label: 'Home' },
  { to: '/chat', label: 'Chat' },
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/digest', label: 'Digest' },
]

/* ── Icon components ───────────────────────────────────────────────── */
function PulseIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <rect width="32" height="32" rx="8" fill="#7F77DD" />
      <path
        d="M7 16h3.5l2.5-6 3.5 12 2.5-8 2.5 4H25"
        stroke="white"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function SearchIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="8" cy="8" r="5.5" />
      <path d="M12.5 12.5L16 16" />
    </svg>
  )
}

function BellIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 2a4.5 4.5 0 0 0-4.5 4.5c0 3.5-1.5 4.5-1.5 4.5h12s-1.5-1-1.5-4.5A4.5 4.5 0 0 0 9 2Z" />
      <path d="M7.5 15a1.5 1.5 0 0 0 3 0" />
    </svg>
  )
}

function ChevronDownIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 4.5L6 7.5l3-3" />
    </svg>
  )
}

/* ── Navbar ─────────────────────────────────────────────────────────── */
export default function Navbar() {
  return (
    <nav className="navbar-dark">
      <div className="navbar-inner">

        {/* ── Left: Logo ─────────────────────────────────────────── */}
        <NavLink to="/" className="navbar-logo">
          <PulseIcon />
          <span className="navbar-logo-text">
            NewsPulse<span className="navbar-logo-accent">AI</span>
          </span>
        </NavLink>

        {/* ── Center: Nav tabs ───────────────────────────────────── */}
        <div className="navbar-tabs">
          {navTabs.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `navbar-tab ${isActive ? 'navbar-tab--active' : ''}`
              }
            >
              {label}
            </NavLink>
          ))}
        </div>

        {/* ── Right: Actions ─────────────────────────────────────── */}
        <div className="navbar-actions">
          <button className="navbar-icon-btn" aria-label="Search">
            <SearchIcon />
          </button>

          <button className="navbar-icon-btn navbar-bell" aria-label="Notifications">
            <BellIcon />
            <span className="navbar-bell-dot" />
          </button>

          <div className="navbar-divider" />

          <button className="navbar-user-btn">
            <div className="navbar-avatar">
              {user.name.split(' ').map(n => n[0]).join('')}
            </div>
            <span className="navbar-username">{user.name}</span>
            <ChevronDownIcon />
          </button>
        </div>
      </div>
    </nav>
  )
}
