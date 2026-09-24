const shapes = {
  bus: (
    <>
      <rect x="5" y="3" width="14" height="16" rx="3" />
      <path d="M5 11h14M8 19v2m8-2v2M9 15h.01M15 15h.01M9 6h6" />
    </>
  ),
  pin: (
    <>
      <path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0Z" />
      <circle cx="12" cy="10" r="2.5" />
    </>
  ),
  home: (
    <>
      <path d="m3 11 9-8 9 8M5 9v12h5v-7h4v7h5V9" />
    </>
  ),
  clock: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v6l4 2" />
    </>
  ),
  star: <path d="m12 2 3 6 7 1-5 5 1 7-6-3-6 3 1-7-5-5 7-1Z" />,
  settings: (
    <>
      <path d="m9 3 1-1h4l1 3 3 1 3 3-2 3 1 3-3 3-3-1-2 3-4-1-1-3-3-2 1-4-1-3 3-2Z" />
      <circle cx="12" cy="11" r="3" />
    </>
  ),
  menu: <path d="M4 6h16M4 12h16M4 18h16" />,
  search: (
    <>
      <circle cx="10" cy="10" r="6" />
      <path d="m15 15 6 6" />
    </>
  ),
  map: <path d="m3 5 6-2 6 2 6-2v16l-6 2-6-2-6 2Zm6-2v16m6-14v16" />,
  layers: (
    <>
      <path d="m12 3 9 6-9 6-9-6Zm-9 11 9 6 9-6M3 18l9 5 9-5" />
    </>
  ),
  back: <path d="m14 5-7 7 7 7M7 12h14" />,
  chevron: <path d="m9 5 7 7-7 7" />,
  share: (
    <>
      <circle cx="18" cy="4" r="3" />
      <circle cx="5" cy="12" r="3" />
      <circle cx="18" cy="20" r="3" />
      <path d="m8 10 7-4M8 14l7 4" />
    </>
  ),
  refresh: (
    <>
      <path d="M20 7V2l-4 4M4 17v5l4-4" />
      <path d="M20 7a9 9 0 0 0-16 1m0 9a9 9 0 0 0 16-1" />
    </>
  ),
  route: (
    <>
      <circle cx="6" cy="4" r="2" />
      <circle cx="18" cy="20" r="2" />
      <path d="M6 6v7a4 4 0 0 0 8 0V8a4 4 0 0 1 8 0v4" />
    </>
  ),
  send: <path d="m3 11 18-8-8 18-2-8Zm8 2L21 3" />,
  swap: <path d="M3 7h17m-4-4 4 4-4 4M21 17H4m4-4-4 4 4 4" />,
  heart: <path d="M12 21 3 12C-2 4 8-1 12 6c4-7 14-2 9 6Z" />,
  locate: (
    <>
      <circle cx="12" cy="12" r="7" />
      <circle cx="12" cy="12" r="2" />
      <path d="M12 1v4m0 14v4M1 12h4m14 0h4" />
    </>
  ),
  list: <path d="M9 5h12M9 12h12M9 19h12M3 5h.1M3 12h.1M3 19h.1" />,
  info: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 11v6M12 7h.01" />
    </>
  ),
  close: <path d="m5 5 14 14M19 5 5 19" />,
};
export default function Icon({ name, size = 22, ...props }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...props}
    >
      {shapes[name] || shapes.bus}
    </svg>
  );
}
