// 화면 확인용 예시 데이터 (Figma 시안 값). 실제 연동 시 FastAPI 응답으로 바꾸면 된다.

export const sampleBeach = {
  name: '화진해수욕장',
  region: '경상북도 포항시 · 경북권역',
  size: '길이 750m · 너비 75m',
  weekLabel: '11월 2주',
  averagePercent: 10.4,
  species: [
    { name: '노무라입깃(유해)', value: 2.4 },
    { name: '보름달물', value: 3.6 },
    { name: '기타', value: 4.7 },
  ],
};

export const sampleForecast = {
  items: [
    { weeks: 1, week: '11월 3주', percent: 12.1 },
    { weeks: 2, week: '11월 4주', percent: 4.2 },
    { weeks: 4, week: '12월 2주', percent: 11.2 },
  ],
  reportDate: '2026.10.30',
};

export const sampleObservation = {
  reportDate: '2026.10.30',
  regionName: '경북',
  regionRate: 4.2,
  station: '포항 부이',
  stationDistance: '38.3km',
  weekLabel: '11월 2주',
  avgTemp: '19.6°C',
  latestLabel: '가장 최근 관측 (2026-11-09 주)',
  latestTemp: '수온 20.4°C',
};

export const sampleNotice = {
  message: '2026-10-30 주간보고를 넣은 모델 예측입니다.',
  model: '효섭 로지스틱 모델 · 권역예측 테이블',
};

// 5월 1주 ~ 12월 4주 (32주) 예시 곡선
const MONTHS = [5, 6, 7, 8, 9, 10, 11, 12];
const bell = (i, peak, center, width, floor = 1) => +(floor + (peak - floor) * Math.exp(-((i - center) ** 2) / (2 * width ** 2))).toFixed(1);
export const sampleSeason = MONTHS.flatMap((m, mi) =>
  [1, 2, 3, 4].map((w, wi) => {
    const i = mi * 4 + wi;
    return {
      label: `${m}월 ${w}주`,
      total: bell(i, 63, 13.5, 5.2, 2),
      nomura: bell(i, 35, 13.5, 3.4, 0.5),
      moon: bell(i, 17, 12.5, 7, 2),
      other: bell(i, 12, 12.5, 7, 1),
    };
  }),
);
export const sampleSelectedIndex = 25; // 11월 2주
