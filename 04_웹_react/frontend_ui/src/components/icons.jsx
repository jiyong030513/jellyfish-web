/* 아이콘 (아이콘/검색 · 달력 · 새로고침 · 전국보기, 브랜드/로고)
   모두 currentColor 선 아이콘이라 color 로 색을 바꾼다.
   ※ 로고(해파리)는 시트 모양을 따라 그린 근사본입니다. Figma 원본 SVG를 내보내면
     <BrandLogo src="/logo.svg" /> 처럼 교체할 수 있어요. */

const base = (size) => ({
  width: size,
  height: size,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.6,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
  'aria-hidden': true,
  focusable: false,
});

export function SearchIcon({ size = 20, ...rest }) {
  return (
    <svg {...base(size)} {...rest}>
      <circle cx="11" cy="11" r="6.5" />
      <path d="M16 16l4 4" />
    </svg>
  );
}

export function CalendarIcon({ size = 20, ...rest }) {
  return (
    <svg {...base(size)} {...rest}>
      <rect x="4" y="5.5" width="16" height="14.5" rx="2.5" />
      <path d="M4 10h16M8.5 3.5v4M15.5 3.5v4" />
    </svg>
  );
}

export function RefreshIcon({ size = 20, ...rest }) {
  return (
    <svg {...base(size)} {...rest}>
      <path d="M19 12a7 7 0 0 1-12.2 4.7M5 12a7 7 0 0 1 12.2-4.7" />
      <path d="M17.6 3.8v3.6H14M6.4 20.2v-3.6H10" />
    </svg>
  );
}

export function ExpandIcon({ size = 16, ...rest }) {
  return (
    <svg {...base(size)} {...rest}>
      <path d="M4 9V5.5A1.5 1.5 0 0 1 5.5 4H9M15 4h3.5A1.5 1.5 0 0 1 20 5.5V9M20 15v3.5a1.5 1.5 0 0 1-1.5 1.5H15M9 20H5.5A1.5 1.5 0 0 1 4 18.5V15" />
    </svg>
  );
}

export function JellyfishIcon({ size = 24, ...rest }) {
  return (
    <svg {...base(size)} {...rest}>
      <path d="M4 12.5a8 8 0 0 1 16 0z" />
      <path d="M8 12.5v3.2c0 1.2-.9 1.6-.9 2.8M12 12.5v6.5M16 12.5v3.2c0 1.2.9 1.6.9 2.8" />
    </svg>
  );
}
