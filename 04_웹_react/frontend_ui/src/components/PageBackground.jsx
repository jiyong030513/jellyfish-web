/* 페이지 뒷배경 — Figma 배경 이미지(1440×1936)를 네 모서리 조각으로 나눈 것
   화면 폭이 1440보다 넓거나 좁아도 도형이 항상 화면 가장자리에 붙고,
   페이지 길이가 달라져도 아래 두 도형은 페이지 맨 아래에 붙는다.
   조각 가장자리는 투명하게 번지게 처리해서 배경색(#050506) 위에 이음매 없이 겹친다.

   사용법: 페이지 맨 바깥 요소(position: relative) 안 첫 줄에 <PageBackground /> 를 넣고,
          실제 내용은 position: relative; z-index: 1 로 위에 올린다. */
import topLeft from '../assets/background/top-left.webp';
import topRight from '../assets/background/top-right.webp';
import bottomLeft from '../assets/background/bottom-left.webp';
import bottomRight from '../assets/background/bottom-right.webp';
import './PageBackground.css';

const PIECES = [
  { key: 'tl', src: topLeft, w: 380, h: 640 },
  { key: 'tr', src: topRight, w: 800, h: 740 },
  { key: 'bl', src: bottomLeft, w: 700, h: 336 },
  { key: 'br', src: bottomRight, w: 440, h: 556 },
];

export function PageBackground() {
  return (
    <div className="jc-page-bg" aria-hidden="true">
      {PIECES.map((p) => (
        <img
          key={p.key}
          className={`jc-page-bg__piece jc-page-bg__piece--${p.key}`}
          src={p.src}
          width={p.w}
          height={p.h}
          alt=""
          decoding="async"
          draggable="false"
        />
      ))}
    </div>
  );
}
