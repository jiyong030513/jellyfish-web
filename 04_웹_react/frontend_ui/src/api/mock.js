/* 서버가 없을 때 쓰는 예시 응답.
   응답 모양은 실제 FastAPI 와 똑같이 맞춰 두었다 (API.md 참고).
   숫자는 시안 확인용으로 만든 값이며 실제 관측·예측값이 아니다. */
import { weekLabel, addDays, seasonIndex } from './week.js';

// id, 이름, 지역, 권역, 위도, 경도, 길이·너비 (좌표는 대략적인 위치)
const BEACHES = [
  [1, '화진해수욕장', '경상북도 포항시', '경북', 36.258, 129.378, '길이 750m · 너비 75m'],
  [2, '영일대해수욕장', '경상북도 포항시', '경북', 36.056, 129.378, '길이 1,750m · 너비 40m'],
  [3, '월포해수욕장', '경상북도 포항시', '경북', 36.207, 129.371, '길이 1,200m · 너비 50m'],
  [4, '해운대해수욕장', '부산광역시 해운대구', '부산', 35.159, 129.160, '길이 1,450m · 너비 70m'],
  [5, '광안리해수욕장', '부산광역시 수영구', '부산', 35.153, 129.119, '길이 1,400m · 너비 64m'],
  [6, '송정해수욕장', '부산광역시 해운대구', '부산', 35.179, 129.200, '길이 1,200m · 너비 57m'],
  [7, '진하해수욕장', '울산광역시 울주군', '울산', 35.383, 129.346, '길이 1,000m · 너비 40m'],
  [8, '경포해수욕장', '강원특별자치도 강릉시', '강원', 37.806, 128.908, '길이 1,800m · 너비 80m'],
  [9, '속초해수욕장', '강원특별자치도 속초시', '강원', 38.191, 128.601, '길이 1,000m · 너비 50m'],
  [10, '망상해수욕장', '강원특별자치도 동해시', '강원', 37.592, 129.089, '길이 1,400m · 너비 70m'],
  [11, '대천해수욕장', '충청남도 보령시', '충남', 36.307, 126.515, '길이 3,500m · 너비 100m'],
  [12, '만리포해수욕장', '충청남도 태안군', '충남', 36.787, 126.143, '길이 2,500m · 너비 250m'],
  [13, '을왕리해수욕장', '인천광역시 중구', '인천', 37.447, 126.373, '길이 700m · 너비 200m'],
  [14, '상주은모래비치', '경상남도 남해군', '경남', 34.723, 127.991, '길이 2,000m · 너비 120m'],
  [15, '함덕해수욕장', '제주특별자치도 제주시', '제주', 33.543, 126.669, '길이 900m · 너비 50m'],
  [16, '협재해수욕장', '제주특별자치도 제주시', '제주', 33.394, 126.240, '길이 900m · 너비 60m'],
  [17, '중문색달해수욕장', '제주특별자치도 서귀포시', '제주', 33.245, 126.412, '길이 560m · 너비 50m'],
].map(([id, name, city, region, lat, lng, size]) => ({ id, name, city, region, lat, lng, size }));

// 해수욕장마다 조금씩 다른 값이 나오도록 하는 고정 난수
const rand = (seed) => {
  const x = Math.sin(seed * 9301 + 49297) * 233280;
  return x - Math.floor(x);
};
const round1 = (v) => Math.round(v * 10) / 10;
const bell = (i, peak, center, width, floor = 1) => round1(floor + (peak - floor) * Math.exp(-((i - center) ** 2) / (2 * width ** 2)));

function seasonOf(b) {
  const peak = 25 + rand(b.id) * 55;
  const center = 12 + rand(b.id + 7) * 4;
  return Array.from({ length: 32 }, (_, i) => ({
    label: `${5 + Math.floor(i / 4)}월 ${(i % 4) + 1}주`,
    total: bell(i, peak, center, 5.2, 2),
    nomura: bell(i, peak * 0.55, center, 3.4, 0.5),
    moon: bell(i, peak * 0.27, center - 1, 7, 2),
    other: bell(i, peak * 0.19, center - 1, 7, 1),
  }));
}

const valueAt = (season, date, key = 'total') => {
  const i = seasonIndex(date);
  return i == null ? null : season[i][key];
};

const delay = (ms) => new Promise((r) => setTimeout(r, ms));

export async function mockBeaches({ date }) {
  await delay(500);
  return {
    date,
    week_label: weekLabel(date),
    beaches: BEACHES.map((b) => {
      const s = seasonOf(b);
      return {
        id: b.id, name: b.name, region: `${b.city} · ${b.region}권역`, lat: b.lat, lng: b.lng,
        average_percent: valueAt(s, date),
        forecast_percent: Object.fromEntries([1, 2, 4].map((w) => [w, valueAt(s, addDays(date, w * 7))])),
      };
    }),
  };
}

export async function mockBeachDetail(id, { date }) {
  await delay(700);
  const b = BEACHES.find((x) => x.id === Number(id));
  if (!b) throw new Error(`해수욕장 ${id} 없음`);
  const s = seasonOf(b);
  const i = seasonIndex(date);
  return {
    beach: {
      id: b.id, name: b.name, region: `${b.city} · ${b.region}권역`, size: b.size,
      week_label: weekLabel(date),
      average_percent: valueAt(s, date),
      species: [
        { name: '노무라입깃(유해)', value: i == null ? null : s[i].nomura },
        { name: '보름달물', value: i == null ? null : s[i].moon },
        { name: '기타', value: i == null ? null : s[i].other },
      ],
    },
    forecast: {
      items: [1, 2, 4].map((w) => ({ weeks: w, week: weekLabel(addDays(date, w * 7)), percent: valueAt(s, addDays(date, w * 7)) })),
      report_date: '2026.10.30',
    },
    observation: {
      report_date: '2026.10.30',
      region_name: b.region,
      region_rate: round1(2 + rand(b.id + 3) * 10),
      station: `${b.city.split(' ').pop().replace(/[시군구]$/, '')} 부이`,
      station_distance: `${round1(5 + rand(b.id + 5) * 40)}km`,
      avg_temp: `${round1(17 + rand(b.id + 9) * 5)}°C`,
      latest_label: '가장 최근 관측 (2026-11-09 주)',
      latest_temp: `수온 ${round1(18 + rand(b.id + 11) * 5)}°C`,
    },
    notice: {
      message: '2026-10-30 주간보고를 넣은 모델 예측입니다.',
      model: '효섭 로지스틱 모델 · 권역예측 테이블',
    },
    season: { data: s, selected_index: i, is_example: true },
  };
}

/* 챗봇 예시 답변 — 실제로는 이지용님 FastAPI /chat 이 Gemini 로 답한다 */
const EMERGENCY = /숨|호흡|의식|어지러|가슴|경련|구토|전신|두드러기|쓰러/;
export async function mockChat({ message, beach_id, horizon_weeks }) {
  await delay(900);
  const b = BEACHES.find((x) => x.id === beach_id);
  if (EMERGENCY.test(message)) {
    return {
      answer: '호흡 곤란이나 의식 저하 같은 증상은 위급할 수 있어요. 지금 바로 119에 신고하고, 구조를 기다리는 동안 환자를 물 밖 안전한 곳에 눕혀 주세요.',
      emergency: true, forecast: [],
      sources: [{ 기관: '보건복지부·중앙응급의료센터', url: 'https://www.e-gen.or.kr' }],
    };
  }
  if (/쏘|쏘였|따가|통증|응급/.test(message)) {
    return {
      answer: '1. 바로 물 밖으로 나와 안전한 곳으로 옮기세요.\n2. 쏘인 곳을 바닷물로 15분 이상 씻어 주세요. 수돗물·식초는 쓰지 마세요.\n3. 남은 촉수는 장갑이나 카드로 조심스럽게 떼어 내세요. 문지르면 안 돼요.\n4. 45℃ 정도의 따뜻한 물로 20분쯤 찜질하면 통증이 줄어요.\n숨쉬기 힘들거나 어지러우면 바로 119에 신고하세요.',
      emergency: false, forecast: [],
      sources: [
        { 기관: '보건복지부·중앙응급의료센터', url: 'https://www.e-gen.or.kr' },
        { 기관: '국립수산과학원', url: 'https://www.nifs.go.kr' },
      ],
    };
  }
  if (b && /위험|괜찮|가도|수영|예측|오늘|다음/.test(message)) {
    return {
      answer: `${b.name}의 ${horizon_weeks ?? 1}주 뒤 예측은 화면 오른쪽 '예측 위험 지수' 카드와 같아요. 물에 들어가기 전 안전요원 안내를 확인하고, 해파리가 보이면 가까이 가지 말고 바로 알려 주세요.`,
      emergency: false, forecast: [],
      sources: [{ 기관: '젤리캐스트 예측 모델', url: '' }],
    };
  }
  return {
    answer: '해파리에 쏘였을 때 대처법, 예방 수칙, 해수욕장별 위험도를 물어보실 수 있어요. 예: "해파리에 쏘이면 어떻게 해?"',
    emergency: false, forecast: [],
    sources: [{ 기관: '행정안전부', url: 'https://www.mois.go.kr' }],
  };
}
