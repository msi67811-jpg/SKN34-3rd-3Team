import React, { useState, useEffect, useCallback, useRef } from 'react';
import { createPortal } from 'react-dom';
import { useApi, api } from './api.js';
const DEADLINES = [
    { id: 'ysa-15', dday: 'D-8', tone: 'urgent', title: '청년창업사관학교 15기', meta: '중소벤처기업진흥공단 · 최대 1억 원' },
    { id: 'seoul-deposit', dday: 'D-24', tone: 'soon', title: '서울 청년창업 임차보증금 지원', meta: '서울시 · 최대 3,000만 원' },
    { id: 'semas-voucher', dday: 'D-37', tone: 'normal', title: '1인 소상공인 판로개척 바우처', meta: '소상공인시장진흥공단 · 최대 500만 원' },
    { id: 'first-step', dday: '상시', tone: 'normal', title: '소상공인 첫걸음 컨설팅', meta: '소상공인시장진흥공단 · 상시 접수' },
  ];

  const HERO_TITLE = [
    ['흩어진', '청년', '창업', '지원', '공고를'],
    ['한', '곳에서', '봅니다'],
  ];

  const METRICS = [
    { value: 168, suffix: '개', label: '연동 주관 기관' },
    { value: 17, suffix: '개 시·도', label: '지역 커버리지' },
    { value: 1842, suffix: '건', label: '모집 중 공고' },
    { value: 50, suffix: '%', label: '최대 세액 감면율' },
  ];

  const CHAT = [
    { role: 'user', text: '대전에서 IT 서비스로 창업하려는데, 받을 수 있는 지원사업이 있을까요?' },
    { role: 'ai', text: "만 39세 이하 예비창업자라면 '예비창업패키지'와 '대전 청년창업 지원'을 함께 검토할 수 있어요. 둘 다 사업화 자금과 멘토링을 제공합니다." },
    { role: 'user', text: '세액 감면도 되나요?' },
    { role: 'ai', text: '창업 후 5년간 소득세를 최대 50% 감면받을 수 있어요(조특법 제6조). 대전은 수도권 밖이라 감면 폭이 더 큽니다.' },
    { role: 'user', text: '부가세 신고는 언제 하죠?' },
    { role: 'ai', text: '일반과세자는 4월·10월 예정신고, 1월·7월 확정신고예요. 다음 신고일 10월 25일을 캘린더에 등록해 둘게요.' },
  ];

  const ROADMAP = [
    { k: 'A', phase: '창업 전', t: '아이디어 검증', d: '업종 창·폐업률과 상권 확인' },
    { k: 'B', phase: '준비', t: '사업자 등록', d: '유형 진단 후 홈택스 신청' },
    { k: 'C', phase: '준비', t: '지원사업 신청', d: '조건 맞는 공고 매칭·접수' },
    { k: 'D', phase: '준비', t: '자금 조달', d: '정책자금·보증 연계' },
    { k: 'E', phase: '창업 후', t: '세액감면 신청', d: '조특법 제6조 대상 판정' },
    { k: 'F', phase: '창업 후', t: '첫 매출·신고', d: '부가세·원천세 일정 관리' },
    { k: 'Z', phase: '성장', t: '스케일업', d: 'R&D·후속 투자 지원 탐색', accent: true },
  ];

  const ROADMAP_TASKS = {
    A: ['업종 창·폐업률과 상권 데이터 확인', '타깃 고객 3명 이상 인터뷰', '경쟁 서비스 5개 비교표 작성', '수익 모델 한 장 정리'],
    B: ['개인/법인 사업자 유형 결정', '업종코드(정보통신업) 확인', '홈택스 사업자등록 신청', '사업용 계좌·카드 개설'],
    C: ['조건 맞는 공고 필터링·선정', '사업계획서(PSST) 초안 작성', '접수 마감일 캘린더 등록', '가점 항목(청년·지역) 확인'],
    D: ['소요 자금 계획표 작성', '정책자금·보증(신보/기보) 상품 비교', 'IR·자금소요 자료 준비', '집행·정산 규정 숙지'],
    E: ['조특법 제6조 감면 요건 확인', '법인세·소득세 신고 시 감면 신청서 제출', '지방세(취득세·재산세) 감면 별도 신청', '감면 배제 업종 여부 재확인'],
    F: ['부가세 예정·확정신고', '직원 있으면 원천세 신고', '경비 증빙 정리 루틴 만들기', '종합소득세/법인세 신고 준비'],
    Z: ['R&D 과제(디딤돌 등) 탐색', '후속 투자·스케일업 프로그램 지원', '채용·조직 계획 수립', '지표(매출·고객) 대시보드 구축'],
  };

  const NAV_MENU = [
    { key: 'roadmap', label: '창업 로드맵', desc: '아이디어부터 스케일업까지' },
    { key: 'tax', label: 'AI 세무 Assistant', desc: '세액감면 자동 판정·경비처리' },
    { key: 'gov', label: '공고문 AI 분석', desc: '지원대상·기간·서류 구조화' },
    { key: 'ai', label: 'AI 상담', desc: '대화형 세무 어시스턴트' },
    { key: 'mypage', label: '마이페이지', desc: '내 맞춤 대시보드' },
  ];

  const PAGES = {
    tax: {
      title: '세금상담',
      lead: '사업자 유형별 세액감면 판정과 부가세 · 종합소득세 신고 일정을 한눈에 정리해 드립니다.',
      body: '판정 결과에는 근거 조문(조특법 제6조 등)이 함께 표시되고, 추가로 궁금한 점은 AI 상담으로 이어집니다.',
      sections: [
        { h: '세액감면 판정', p: '창업 지역과 업종에 따라 5년간 50~100% 감면 대상 여부를 근거 조문과 함께 알려드립니다.' },
        { h: '신고 캘린더', p: '부가세 예정·확정신고, 종합소득세, 원천세 일정을 한 화면에 모아 마감 전에 알림을 보냅니다.' },
        { h: '증빙 체크리스트', p: '경비로 인정되는 지출과 필요한 증빙 서류를 거래 유형별로 정리했습니다.' },
      ],
    },
    gov: {
      title: '정부지원사업',
      lead: '중앙부처 · 지자체 · 공공기관 공고를 매일 09:00에 모아 내 조건에 맞는 사업만 골라 보여드립니다.',
      body: '현재 168개 기관 · 17개 시·도 공고를 큐레이션하고 있어요.',
      sections: [
        { h: '자금 지원', p: '창업사업화, R&D, 시설·운전자금 융자까지 지원 유형별로 분류해 제공합니다.' },
        { h: '공간 · 보육', p: '창업보육센터, 메이커스페이스, 지역 창업허브 입주 공고를 지역별로 모았습니다.' },
        { h: '마감 알림', p: '관심 공고를 저장하면 마감 3일 전 알림을 보내 접수 기한을 놓치지 않게 합니다.' },
      ],
    },
    ai: {
      title: 'AI 상담',
      lead: '경비처리, 부가세 신고, 사업자 유형 등 세무 질문에 근거 문서와 함께 답변합니다.',
      body: '대화 한 번으로 지원사업 매칭부터 신고 일정 등록까지 이어서 처리할 수 있어요.',
      sections: [
        { h: '근거 기반 답변', p: '국세청 해석사례와 관련 법령을 인용해, 답변마다 출처를 함께 제시합니다.' },
        { h: '내 사업 맥락 반영', p: '등록한 사업자 정보(업종·지역·매출 규모)를 반영해 상황에 맞는 안내를 제공합니다.' },
        { h: '상담 이력 저장', p: '지난 질문과 답변을 저장해 두고 필요할 때 다시 찾아볼 수 있습니다.' },
      ],
    },
  };

  /* --- 마이페이지 데이터 (첨부 이미지 기준) --- */
  const MP_SCHEDULE = [
    { title: '예비창업패키지 마감', when: 'D-43' },
    { title: '부가세 2기 예정신고', when: '10월 25일' },
    { title: '종소세 중간예납', when: '11월 30일' },
  ];
  const MP_RECO = [
    { title: '청년창업사관학교', score: 92 },
    { title: '초기창업패키지', score: 88 },
    { title: '대전 청년창업', score: 81 },
  ];
  const MP_CONSULTS = ['경비처리 가능 여부 문의', '부가세 신고 방법 문의', '사업자 유형 관련 문의'];

  const MP_MENU = [
    { key: 'home', label: '홈 (대시보드)' },
    { key: 'ai', label: 'AI 상담' },
    { group: '세무관리' },
    { key: 'biz-type', label: '사업자유형 진단', sub: true },
    { key: 'tax-cut', label: '세액감면 판정', sub: true },
    { key: 'tax-cal', label: '세금 일정', sub: true },
    { group: '지원정책' },
    { key: 'explore', label: '탐색', sub: true },
    { key: 'saved', label: '저장한 정책', sub: true },
    { key: 'spend', label: '지출관리', tag: 'BETA' },
    { divider: true },
    { key: 'settings', label: '프로필 · 설정' },
  ];

  const CAL_START = { y: 2025, m: 9 };
  const CAL_TODAY = '2025-10-08';
  const CAL_EVENTS = {
    '2025-10-08': [{ type: 'tax', title: '원천세 신고·납부', note: '전월 급여 지급분' }],
    '2025-10-14': [{ type: 'policy', title: '청년창업사관학교 15기 마감', note: '중소벤처기업진흥공단' }],
    '2025-10-25': [
      { type: 'tax', title: '부가세 2기 예정신고', note: '홈택스 전자신고' },
      { type: 'policy', title: '초기창업패키지 실적 보고', note: '창업진흥원' },
    ],
    '2025-10-30': [{ type: 'policy', title: '서울 청년창업 임차보증금 지원 마감', note: '서울시' }],
    '2025-11-06': [{ type: 'policy', title: '1인 소상공인 판로개척 바우처 마감', note: '소상공인시장진흥공단' }],
    '2025-11-17': [{ type: 'policy', title: '예비창업패키지 서류 발표', note: '창업진흥원' }],
    '2025-11-30': [{ type: 'tax', title: '종합소득세 중간예납', note: '11월 30일까지 납부' }],
  };
  const WEEKDAYS = ['일', '월', '화', '수', '목', '금', '토'];
  const pad2 = (n) => String(n).padStart(2, '0');
  const dayKey = (y, m, d) => `${y}-${pad2(m + 1)}-${pad2(d)}`;

  const prefersReducedMotion =
    typeof window !== 'undefined' && window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- 공용 훅 ---------- */
  function useInView(opts, repeat) {
    const ref = useRef(null);
    const [inView, setInView] = useState(false);
    useEffect(() => {
      if (typeof IntersectionObserver === 'undefined') {
        setInView(true);
        return;
      }
      const el = ref.current;
      const io = new IntersectionObserver(
        (entries) => {
          entries.forEach((e) => {
            if (e.isIntersecting) {
              setInView(true);
              if (!repeat) io.disconnect();
            } else if (repeat) {
              setInView(false);
            }
          });
        },
        opts || { threshold: 0.16, rootMargin: '0px 0px -10% 0px' }
      );
      if (el) io.observe(el);
      const failsafe = repeat ? null : setTimeout(() => setInView(true), 2800);
      return () => {
        io.disconnect();
        if (failsafe) clearTimeout(failsafe);
      };
    }, [repeat]);
    return [ref, inView];
  }

  function Reveal({ children, delay = 0, as: Tag = 'div', className = '' }) {
    const [ref, inView] = useInView(undefined, true);
    const shown = prefersReducedMotion || inView;
    return (
      <Tag
        ref={ref}
        className={`reveal ${shown ? 'is-in' : ''} ${className}`.trim()}
        style={{ '--d': `${delay}ms` }}
      >
        {children}
      </Tag>
    );
  }

  function useCountUp(target, run, duration = 1200) {
    const [value, setValue] = useState(prefersReducedMotion ? target : 0);
    useEffect(() => {
      if (prefersReducedMotion) {
        setValue(target);
        return;
      }
      if (!run) {
        setValue(0);
        return;
      }
      let raf;
      const start = performance.now();
      const tick = (now) => {
        const p = Math.min(1, (now - start) / duration);
        setValue(Math.round(target * (1 - Math.pow(1 - p, 3))));
        if (p < 1) raf = requestAnimationFrame(tick);
      };
      raf = requestAnimationFrame(tick);
      return () => cancelAnimationFrame(raf);
    }, [target, run, duration]);
    return value;
  }

  function Metric({ value, suffix, label, delay }) {
    const [ref, inView] = useInView({ threshold: 0.5 }, true);
    const n = useCountUp(value, inView);
    return (
      <div className="reveal metric is-in" ref={ref} style={{ '--d': `${delay}ms` }}>
        <b className="u-num">
          {n.toLocaleString()}
          {suffix}
        </b>
        <span>{label}</span>
      </div>
    );
  }

  function ScrollProgress() {
    const ref = useRef(null);
    useEffect(() => {
      let raf = 0;
      const onScroll = () => {
        if (raf) return;
        raf = requestAnimationFrame(() => {
          raf = 0;
          const h = document.documentElement;
          const max = h.scrollHeight - h.clientHeight;
          const p = max > 0 ? h.scrollTop / max : 0;
          if (ref.current) ref.current.style.setProperty('--p', p.toFixed(4));
        });
      };
      window.addEventListener('scroll', onScroll, { passive: true });
      onScroll();
      return () => window.removeEventListener('scroll', onScroll);
    }, []);
    return <div className="progress" ref={ref} aria-hidden="true" />;
  }

  function useThemeToggle() {
    return useCallback(() => {
      const isDark =
        document.documentElement.getAttribute('data-theme') === 'dark' ||
        (!document.documentElement.getAttribute('data-theme') &&
          window.matchMedia('(prefers-color-scheme: dark)').matches);
      document.documentElement.setAttribute('data-theme', isDark ? 'light' : 'dark');
    }, []);
  }

  /* ---------- 메뉴 드로어 ---------- */
  function MenuDrawer({ open, onClose, onNavigate, user, onAuth }) {
    useEffect(() => {
      if (!open) return;
      const prev = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      const onKey = (e) => e.key === 'Escape' && onClose();
      window.addEventListener('keydown', onKey);
      return () => {
        document.body.style.overflow = prev;
        window.removeEventListener('keydown', onKey);
      };
    }, [open, onClose]);

    const node = (
      <div className={'drawer-root' + (open ? ' is-open' : '')} aria-hidden={!open}>
        <div className="drawer-overlay" onClick={onClose} />
        <aside className="drawer" role="dialog" aria-modal="true" aria-label="전체 메뉴">
          <div className="drawer__top">
            <span className="drawer__brand">
              <span className="brand__mark" aria-hidden="true">ON</span>창업ON
            </span>
            <button className="drawer__close" type="button" onClick={onClose} aria-label="메뉴 닫기">×</button>
          </div>
          <ul className="drawer__list">
            {NAV_MENU.map((m, i) => (
              <li className="drawer__item" key={m.key} style={{ '--i': i }}>
                <button
                  className="drawer__link"
                  type="button"
                  onClick={() => {
                    onClose();
                    onNavigate(m.key);
                  }}
                >
                  <span className="drawer__num">{pad2(i + 1)}</span>
                  <span>{m.label}</span>
                  <span className="drawer__desc">{m.desc}</span>
                </button>
              </li>
            ))}
          </ul>
          <div className="drawer__foot">
            {user ? (
              <React.Fragment>
                <div className="drawer__auth">
                  <span><b>{user.name}</b>님으로 로그인됨</span>
                  <button className="btn btn--ghost" type="button"
                    onClick={() => { onClose(); onAuth(); }}>로그아웃</button>
                </div>
              </React.Fragment>
            ) : (
              <React.Fragment>
                <button className="btn btn--primary drawer__login" type="button"
                  onClick={() => { onClose(); onAuth(); }}>로그인</button>
                <p className="drawer__hint">로그인하면 맞춤 공고와 세무 대시보드가 열립니다.</p>
              </React.Fragment>
            )}
          </div>
        </aside>
      </div>
    );
    return createPortal(node, document.body);
  }

  /* ---------- 로그인 / 회원가입 모달 ---------- */
  const inputStyle = {
    width: '100%', padding: '11px 12px', font: 'inherit', fontSize: 13.5, color: 'var(--ink)',
    background: 'var(--ground)', border: '1px solid var(--line-strong)', borderRadius: 10,
  };
  const linkBtn = {
    border: 0, background: 'transparent', padding: 0, font: 'inherit', fontWeight: 700,
    color: 'var(--blue-deep)', cursor: 'pointer', textDecoration: 'underline',
  };
  const fieldLabel = { display: 'block', marginBottom: 5, fontSize: 12, fontWeight: 600, color: 'var(--ink-soft)' };
  const socialBtn = {
    width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
    padding: '11px 12px', border: 0, borderRadius: 11, fontSize: 13.5, fontWeight: 700, cursor: 'pointer',
  };

  function LoginModal({ onClose, onSuccess }) {
    const [mode, setMode] = useState('login'); // 'login' | 'signup'
    const [name, setName] = useState('');
    const [email, setEmail] = useState('jeong@changeup.kr');
    const [pw, setPw] = useState('changeup');
    const [pw2, setPw2] = useState('');
    const [err, setErr] = useState('');

    useEffect(() => {
      const onKey = (e) => e.key === 'Escape' && onClose();
      window.addEventListener('keydown', onKey);
      return () => window.removeEventListener('keydown', onKey);
    }, [onClose]);

    const finish = (displayName) =>
      onSuccess({ name: displayName || name || '정석', email, biz: '정보통신업', region: '대전광역시' });

    const submit = (e) => {
      e.preventDefault();
      if (mode === 'signup' && pw !== pw2) { setErr('비밀번호가 일치하지 않습니다.'); return; }
      setErr('');
      finish(mode === 'signup' ? name : '정석');
    };

    const isLogin = mode === 'login';

    return (
      <div onMouseDown={(e) => e.target === e.currentTarget && onClose()}
        style={{
          position: 'fixed', inset: 0, zIndex: 90, display: 'grid', placeItems: 'center',
          padding: '20px', background: 'rgba(12,16,30,0.46)', backdropFilter: 'blur(3px)',
        }}>
        <div role="dialog" aria-modal="true" aria-labelledby="login-title"
          style={{
            width: '100%', maxWidth: 380, maxHeight: '90vh', overflowY: 'auto', background: 'var(--surface-solid)',
            border: '1px solid var(--line)', borderRadius: 18, boxShadow: 'var(--shadow)',
            padding: '26px 24px 24px',
          }}>
          <button type="button" onClick={onClose} aria-label="닫기"
            style={{
              float: 'right', width: 28, height: 28, margin: '-6px -6px 0 0', border: 0,
              borderRadius: 8, background: 'transparent', color: 'var(--ink-faint)', fontSize: 18, cursor: 'pointer',
            }}>×</button>
          <h2 id="login-title" style={{ margin: '0 0 4px', fontSize: 18, fontWeight: 700, letterSpacing: '-0.02em' }}>
            {isLogin ? '창업ON 로그인' : '창업ON 회원가입'}
          </h2>
          <p style={{ margin: '0 0 18px', fontSize: 12.5, color: 'var(--ink-soft)' }}>
            {isLogin ? '사업자 정보로 맞춤 대시보드를 불러옵니다.' : '3분이면 가입하고 맞춤 추천을 받아요.'}
          </p>

          <form onSubmit={submit}>
            {!isLogin && (
              <label style={{ display: 'block', marginBottom: 12 }}>
                <span style={fieldLabel}>이름</span>
                <input value={name} onChange={(e) => setName(e.target.value)} placeholder="홍길동" autoComplete="name" style={inputStyle} required />
              </label>
            )}
            <label style={{ display: 'block', marginBottom: 12 }}>
              <span style={fieldLabel}>이메일</span>
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="username" style={inputStyle} required />
            </label>
            <label style={{ display: 'block', marginBottom: 12 }}>
              <span style={fieldLabel}>비밀번호</span>
              <input type="password" value={pw} onChange={(e) => setPw(e.target.value)}
                autoComplete={isLogin ? 'current-password' : 'new-password'} style={inputStyle} required />
            </label>
            {!isLogin && (
              <label style={{ display: 'block', marginBottom: 12 }}>
                <span style={fieldLabel}>비밀번호 확인</span>
                <input type="password" value={pw2} onChange={(e) => setPw2(e.target.value)} autoComplete="new-password" style={inputStyle} required />
              </label>
            )}
            {err && <p style={{ margin: '0 0 10px', fontSize: 12, color: 'var(--red)' }}>{err}</p>}
            <button type="submit"
              style={{
                width: '100%', marginTop: 6, padding: 12, border: 0, borderRadius: 11,
                background: 'linear-gradient(135deg, var(--blue), var(--blue-deep))', color: '#fff',
                fontSize: 14, fontWeight: 700, cursor: 'pointer',
              }}>{isLogin ? '로그인' : '가입하기'}</button>
          </form>

          {/* 소셜 로그인 (로그인 버튼 아래) */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, margin: '16px 0 12px', color: 'var(--ink-faint)', fontSize: 11 }}>
            <span style={{ flex: 1, height: 1, background: 'var(--line)' }} />또는<span style={{ flex: 1, height: 1, background: 'var(--line)' }} />
          </div>
          <div style={{ display: 'grid', gap: 8 }}>
            <button type="button" onClick={() => finish('카카오 사용자')} style={{ ...socialBtn, background: '#FEE500', color: '#191919' }}>
              <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" fill="#191919">
                <path d="M12 3C6.48 3 2 6.54 2 10.8c0 2.76 1.86 5.18 4.66 6.55-.15.53-.7 2.5-.8 2.9-.12.48.18.47.37.35.15-.1 2.4-1.63 3.37-2.28.66.1 1.34.15 2 .15 5.52 0 10-3.54 10-7.9S17.52 3 12 3z" />
              </svg>
              카카오로 계속하기
            </button>
            <button type="button" onClick={() => finish('네이버 사용자')} style={{ ...socialBtn, background: '#03C75A', color: '#fff' }}>
              <span style={{ fontFamily: 'system-ui, sans-serif', fontWeight: 900, fontSize: 14 }}>N</span>
              네이버로 계속하기
            </button>
          </div>

          <p style={{ margin: '16px 0 0', fontSize: 12.5, color: 'var(--ink-soft)', textAlign: 'center' }}>
            {isLogin ? '아직 계정이 없으신가요? ' : '이미 계정이 있으신가요? '}
            <button type="button" onClick={() => { setErr(''); setMode(isLogin ? 'signup' : 'login'); }} style={linkBtn}>
              {isLogin ? '회원가입' : '로그인'}
            </button>
          </p>
          {isLogin && (
            <p style={{ margin: '8px 0 0', textAlign: 'center' }}>
              <button type="button" onClick={() => setErr('데모 화면이라 비밀번호 찾기는 지원하지 않습니다.')}
                style={{ ...linkBtn, color: 'var(--ink-faint)', fontWeight: 500 }}>
                비밀번호를 잊으셨나요?
              </button>
            </p>
          )}
          <p style={{ margin: '14px 0 0', fontSize: 11.5, color: 'var(--ink-faint)', textAlign: 'center' }}>
            데모 화면입니다 · 소셜 로그인·회원가입 모두 예시로 바로 로그인됩니다
          </p>
        </div>
      </div>
    );
  }

  /* ---------- 마이페이지 · 실시간 AI 상담 ---------- */
  const AI_RULES =
    '너는 "창업ON"의 세무·창업 지원 상담 어시스턴트야. ' +
    '사용자는 대전광역시에서 정보통신업으로 사업을 준비/운영 중인 예비·초기 창업자야. ' +
    '한국어로 3~5문장 이내로 간결하고 실용적으로 답해. ' +
    '정부지원사업, 세액감면(조특법 제6조 등 창업중소기업 세액감면), 부가가치세·종합소득세 신고 일정, 경비처리 위주로 도와줘. ' +
    '숫자·요건은 일반적인 기준으로 안내하되, 확정 판단이 필요하면 관할 세무서나 세무대리인 확인을 함께 권해. 이 화면은 데모야.';

  const AI_SUGGESTIONS = [
    '정보통신업 창업도 세액감면 대상인가요?',
    '올해 부가세 신고 일정 알려줘',
    '초기 창업자가 받을 수 있는 정부지원사업은?',
    '노트북 구입비도 경비처리 되나요?',
  ];

  const AI_ERR = {
    not_granted: 'AI 사용 권한이 없어 응답을 불러올 수 없어요. claude.ai 뷰어에서 이 아티팩트의 AI 사용을 허용해 주세요.',
    sampling_disabled: '이 계정/조직에서는 AI 응답을 사용할 수 없어요.',
    not_declared: 'AI 기능이 이 버전에 선언되어 있지 않아요.',
    rate_limited: '요청이 많아요. 잠시 후 다시 시도해 주세요.',
    refused: '이 질문에는 답하기 어려워요. 조금 다르게 물어봐 주세요.',
    prompt_too_large: '대화가 너무 길어졌어요. 새로 시작해 주세요.',
    session_expired: '세션이 만료됐어요. 다시 로그인해 주세요.',
  };

  function AiConsult({ user, rules, seed, title, suggestions, large }) {
    const RULES = rules || AI_RULES;
    const CHIPS = suggestions || AI_SUGGESTIONS;
    const [sampleFn, setSampleFn] = useState(undefined); // undefined=연결중, null=불가, fn=사용가능
    const [turns, setTurns] = useState(() => seed || []);
    const [draft, setDraft] = useState('');
    const [stream, setStream] = useState('');
    const [busy, setBusy] = useState(false);
    const [err, setErr] = useState('');
    const bodyRef = useRef(null);
    const ctlRef = useRef(null);

    useEffect(() => {
      let alive = true;
      (async () => {
        try {
          const s = window.claude && (await window.claude.use('sample'));
          if (alive) setSampleFn(() => s || null);
        } catch (e) {
          if (alive) setSampleFn(() => null);
        }
      })();
      return () => {
        alive = false;
        if (ctlRef.current) ctlRef.current.abort();
      };
    }, []);

    useEffect(() => {
      if (bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
    }, [turns, stream, busy]);

    const ask = async (text) => {
      const q = (text || '').trim();
      if (!q || busy) return;
      setErr('');
      const nextTurns = [...turns, { role: 'user', content: q }];
      setTurns(nextTurns);
      setDraft('');
      setBusy(true);
      setStream('');
      const ctl = new AbortController();
      ctlRef.current = ctl;

      // 1) Backend RAG — DB(세법 4,459조문 / 정책)에서 근거 문서 검색
      let rag = null;
      try {
        rag = await api.chat({ question: q, category: 'tax' }, { signal: ctl.signal });
      } catch (e) {
        /* Backend 미실행 시 무시하고 생성만 진행 */
      }
      const sources = (rag && rag.sources) || [];

      try {
        if (sampleFn) {
          // 2) 검색된 근거를 컨텍스트로 넣어 생성 (RAG)
          const ctx = sources.length
            ? '\n\n[DB에서 검색한 근거 문서 — 이 내용을 우선 활용하고 인용한 조문명을 답변에 표기해]\n' +
              sources
                .map((s, i) => `[${i + 1}] ${s.title}\n${(s.excerpt || '').slice(0, 500)}`)
                .join('\n\n')
            : '';
          const res = await sampleFn(
            [{ role: 'user', content: RULES + ctx }, ...nextTurns],
            {
              cache: false,
              modelTier: 'quick',
              signal: ctl.signal,
              onText: ({ text: t }) => setStream(t),
            }
          );
          setTurns((cur) => [...cur, { role: 'assistant', content: res.text, sources }]);
        } else if (rag) {
          // 3) 생성 불가 → Backend/LLM 서비스의 추출형 답변 + 근거
          setTurns((cur) => [...cur, { role: 'assistant', content: rag.answer, sources }]);
        } else {
          setErr(
            'AI 응답을 사용할 수 없어요. Backend(:8000)를 실행하거나 claude.ai에서 열어주세요.'
          );
        }
      } catch (e) {
        const code = e && e.code;
        if (code === 'cancelled') {
          if (e.text) setTurns((cur) => [...cur, { role: 'assistant', content: e.text + ' …(중단됨)' }]);
        } else if (rag) {
          setTurns((cur) => [...cur, { role: 'assistant', content: rag.answer, sources }]);
        } else {
          setErr(AI_ERR[code] || '응답을 불러오지 못했어요. 잠시 후 다시 시도해 주세요.');
          if (e && e.text) {
            setTurns((cur) => [...cur, { role: 'assistant', content: e.text + ' …(오류로 중단됨)' }]);
          }
        }
      } finally {
        setBusy(false);
        setStream('');
        ctlRef.current = null;
      }
    };

    const status =
      sampleFn === undefined
        ? '연결 중…'
        : sampleFn
          ? 'LLM 생성 + DB 근거 검색 (RAG)'
          : 'DB 근거 검색 (Backend RAG)';

    return (
      <div className={'ai' + (large ? ' ai--lg' : '')}>
        <div className="ai__bar">
          <span className="chatbox__ava" aria-hidden="true">ON</span>
          <span className="chatbox__who">
            <b>{title || 'AI 세무·창업 상담'}</b>
            <span>{status}</span>
          </span>
        </div>

        <div className="ai__body" ref={bodyRef}>
          {turns.length === 0 && !busy && (
            <div className="ai__hint">
              {user.biz} · {user.region} 기준으로 답해 드려요. 무엇이든 물어보세요.
              <div className="ai__chips">
                {CHIPS.map((s) => (
                  <button key={s} type="button" className="ai__chip"
                    onClick={() => ask(s)}>
                    {s}
                  </button>
                ))}
              </div>
              {sampleFn === null && (
                <p style={{ marginTop: 14, fontSize: 12 }}>
                  이 화면에서는 실시간 AI 응답을 사용할 수 없어요. claude.ai에서 열고 AI 사용을 허용하면 활성화됩니다.
                </p>
              )}
            </div>
          )}
          {turns.map((m, i) => (
            <React.Fragment key={i}>
              <div className={`msg msg-in msg--${m.role === 'assistant' ? 'ai' : 'user'}`}>
                {m.content}
              </div>
              {m.sources && m.sources.length > 0 && (
                <div className="msg-src">
                  <b>근거 문서 {m.sources.length}건 (DB 검색)</b>
                  {m.sources.map((s, si) => (
                    <a key={si} href={s.url || '#'} target="_blank" rel="noreferrer">
                      [{si + 1}] {s.lawName ? `${s.lawName} · ` : ''}{s.title}
                    </a>
                  ))}
                </div>
              )}
            </React.Fragment>
          ))}
          {busy &&
            (stream ? (
              <div className="msg msg--ai">{stream}</div>
            ) : (
              <div className="typing" aria-label="응답 생성 중"><i /><i /><i /></div>
            ))}
        </div>

        {err && <p className="ai__err">{err}</p>}

        <form className="ai__foot" onSubmit={(e) => { e.preventDefault(); ask(draft); }}>
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="메시지를 입력하세요"
            aria-label="메시지 입력"
            disabled={busy}
          />
          {busy ? (
            <button type="button" className="ai__send" onClick={() => ctlRef.current && ctlRef.current.abort()}>
              중지
            </button>
          ) : (
            <button type="submit" className="ai__send" disabled={!draft.trim()}>
              전송
            </button>
          )}
        </form>
        <p className="ai__note">
          데모 화면입니다 · 답변은 참고용이며, 확정 세무 판단은 전문가 확인이 필요해요.
        </p>
      </div>
    );
  }

  /* ---------- 마이페이지 ---------- */
  /* ===== 마이페이지: 일정 캘린더 (확인 + 추가/삭제) ===== */
  function MpCalendar({ full }) {
    const today = new Date();
    const todayKey = `${today.getFullYear()}-${pad2(today.getMonth() + 1)}-${pad2(today.getDate())}`;
    const [cur, setCur] = useState({ y: today.getFullYear(), m: today.getMonth() });
    const [sel, setSel] = useState(todayKey);
    const [added, setAdded] = useState({}); // 사용자가 직접 추가한 일정
    const [removed, setRemoved] = useState({}); // 숨긴 일정 key `${date}:${idx}`
    const [ftitle, setFtitle] = useState('');
    const [ftype, setFtype] = useState('tax');

    // Backend: GET /api/calendar → 실제 세금·정책 일정. 실패 시 목데이터.
    const { data: fetched } = useApi(
      `/calendar?year=${cur.y}&month=${cur.m + 1}&limit=200`,
      CAL_EVENTS,
      eventsByDate
    );

    // 서버 일정 + 직접 추가분 병합 (삭제 표시된 항목 제외)
    const events = React.useMemo(() => {
      const o = {};
      for (const [k, arr] of Object.entries(fetched || {})) {
        o[k] = arr.map((e) => ({ ...e }));
      }
      for (const [k, arr] of Object.entries(added)) {
        o[k] = [...(o[k] || []), ...arr];
      }
      for (const [k, idxs] of Object.entries(removed)) {
        if (o[k]) o[k] = o[k].filter((_, i) => !idxs.includes(i));
      }
      return o;
    }, [fetched, added, removed]);

    const startDow = new Date(cur.y, cur.m, 1).getDay();
    const daysInMonth = new Date(cur.y, cur.m + 1, 0).getDate();
    const cells = [];
    for (let i = 0; i < startDow; i++) cells.push(null);
    for (let d = 1; d <= daysInMonth; d++) cells.push(d);
    while (cells.length % 7 !== 0) cells.push(null);

    const monthPrefix = `${cur.y}-${pad2(cur.m + 1)}`;
    const monthCount = Object.keys(events).filter((k) => k.startsWith(monthPrefix) && events[k].length).length;
    const shift = (delta) => {
      const nd = new Date(cur.y, cur.m + delta, 1);
      setCur({ y: nd.getFullYear(), m: nd.getMonth() });
    };
    const selEvents = events[sel] || [];
    const [sy, sm, sd] = sel.split('-').map(Number);
    const selLabel = `${sm}월 ${sd}일 (${WEEKDAYS[new Date(sy, sm - 1, sd).getDay()]})`;

    const addEvent = (e) => {
      e.preventDefault();
      const t = ftitle.trim();
      if (!t) return;
      setAdded((p) => ({ ...p, [sel]: [...(p[sel] || []), { type: ftype, title: t, note: '직접 추가' }] }));
      setFtitle('');
    };
    const delEvent = (idx) =>
      setRemoved((p) => ({ ...p, [sel]: [...(p[sel] || []), idx] }));

    return (
      <div className="cal" role="group" aria-label="일정 캘린더" style={full ? { maxWidth: 520 } : undefined}>
        <div className="cal__head">
          <h3 className="cal__title">일정 관리</h3>
          <div className="cal__nav">
            <button type="button" onClick={() => shift(-1)} aria-label="이전 달">‹</button>
            <span className="cal__month">{cur.y}.{pad2(cur.m + 1)}</span>
            <button type="button" onClick={() => shift(1)} aria-label="다음 달">›</button>
          </div>
        </div>
        <p className="cal__sub">이번 달 일정 {monthCount}건</p>
        <div className="cal__grid">
          {WEEKDAYS.map((w, i) => (
            <div key={w} className={'cal__dow' + (i === 0 ? ' cal__dow--sun' : '')}>{w}</div>
          ))}
          {cells.map((d, i) => {
            if (!d) return <div key={`e${i}`} className="cal__day cal__day--out" />;
            const k = dayKey(cur.y, cur.m, d);
            const types = [...new Set((events[k] || []).map((e) => e.type))];
            const isSel = k === sel;
            return (
              <button key={k} type="button"
                className={'cal__day' + (isSel ? ' cal__day--sel' : '') + (k === todayKey && !isSel ? ' cal__day--today' : '')}
                aria-pressed={isSel} onClick={() => setSel(k)}>
                {d}
                {types.length > 0 && (
                  <span className="cal__dot">
                    {types.map((t) => <i key={t} className={t === 'tax' ? 't-tax' : 't-policy'} />)}
                  </span>
                )}
              </button>
            );
          })}
        </div>
        <div className="cal__legend">
          <span><i className="t-tax" /> 세금</span>
          <span><i className="t-policy" /> 지원사업</span>
        </div>
        <div className="cal__events">
          <h4>{selLabel} 일정</h4>
          {selEvents.length === 0 ? (
            <p className="cal__empty">등록된 일정이 없어요.</p>
          ) : (
            selEvents.map((e, idx) => (
              <div key={idx} className="cal__ev">
                <i className={e.type === 'tax' ? 't-tax' : 't-policy'} />
                <div style={{ flex: 1 }}>
                  <b>{e.title}</b>
                  <span>{e.note}</span>
                </div>
                <button className="cal__ev-del" type="button" onClick={() => delEvent(idx)} aria-label="일정 삭제">✕</button>
              </div>
            ))
          )}
          <form className="cal__add" onSubmit={addEvent}>
            <input type="text" value={ftitle} onChange={(e) => setFtitle(e.target.value)}
              placeholder={`${selLabel}에 일정 추가`} aria-label="일정 제목" />
            <button type="submit">추가</button>
            <div className="cal__add-row">
              <select value={ftype} onChange={(e) => setFtype(e.target.value)} aria-label="분류" style={{ flex: 'none' }}>
                <option value="tax">세금</option>
                <option value="policy">지원사업</option>
              </select>
            </div>
          </form>
        </div>
      </div>
    );
  }

  /* ===== 사업자 유형 진단 ===== */
  function BizTypeDiagnosis() {
    const [rev, setRev] = useState('mid');
    const [taxInvoice, setTaxInvoice] = useState('no');
    const [excluded, setExcluded] = useState('no');

    let vat;
    if (excluded === 'yes' || rev === 'high' || taxInvoice === 'yes') vat = '일반과세자';
    else if (rev === 'low') vat = '간이과세자';
    else vat = '간이과세자 (연 매출 1억 400만 원 미만 유지 시)';
    const corp = rev === 'high'
      ? '법인 전환 검토 — 외부 투자 유치, 대표자 급여 비용화, 낮은 세율 구간 활용에 유리'
      : '개인사업자 유지 — 초기 설립·행정 부담이 작고 폐업도 간단';

    const seg = (val, set, opts) => (
      <div className="seg">
        {opts.map(([v, l]) => (
          <button key={v} type="button" aria-pressed={val === v} onClick={() => set(v)}>{l}</button>
        ))}
      </div>
    );

    return (
      <div className="tool">
        <div className="tool__panel">
          <h2>사업자 유형 진단</h2>
          <div className="field-col">
            <label className="fld"><span>예상 연 매출</span>
              {seg(rev, setRev, [['low', '8천만 원 미만'], ['mid', '8천만 ~ 1.5억'], ['high', '1.5억 초과']])}
            </label>
            <label className="fld"><span>세금계산서 발행이 자주 필요한가요? (B2B 거래)</span>
              {seg(taxInvoice, setTaxInvoice, [['no', '아니오'], ['yes', '예']])}
            </label>
            <label className="fld"><span>간이과세 배제 업종인가요? (변호사·병원·도매 등)</span>
              {seg(excluded, setExcluded, [['no', '아니오'], ['yes', '예']])}
            </label>
          </div>
          <div className="result">
            <p className="result__label">추천 과세 유형</p>
            <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--blue-deep)', margin: '4px 0 6px', letterSpacing: '-0.02em' }}>{vat}</div>
            <p className="result__note"><b>개인 / 법인</b> · {corp}</p>
            <p className="result__note">
              창업 초기에는 개인사업자로 시작하고, 매출·투자 규모가 커지면 법인 전환을 검토하는 흐름이 일반적입니다.
              간이과세자는 세금계산서 발행이 제한되므로 거래처 요구가 많으면 일반과세가 유리합니다.
            </p>
            <p className="result__cite">참고용 안내 · 실제 등록 전 관할 세무서·세무대리인 확인을 권장합니다.</p>
          </div>
        </div>
      </div>
    );
  }

  /* ===== 저장한 정책 ===== */
  function SavedPolicies({ saved, onToggleSave, onExplore }) {
    const list = GOV_LISTINGS.filter((g) => saved.has(g.id)).sort((a, b) => a.dday - b.dday);
    return (
      <div className="tool">
        <div className="tool__panel" style={{ marginBottom: 12 }}>
          <h2>저장한 정책 {list.length}건</h2>
          <p style={{ margin: 0, fontSize: 12.5, color: 'var(--ink-soft)' }}>
            <b>탐색</b>에서 ★ 를 누르면 여기에 모이고, 마감일은 캘린더에도 표시됩니다.
          </p>
        </div>
        {list.length === 0 ? (
          <div className="gov__empty">
            저장한 정책이 없어요.{' '}
            <button type="button" onClick={onExplore} style={linkBtn}>탐색하러 가기</button>
          </div>
        ) : (
          <ul className="gov__list">
            {list.map((g) => (
              <li className="gov__card" key={g.id}>
                <h3>{g.title}</h3>
                <span className={'gov__dday' + (g.dday <= 10 ? ' gov__dday--urgent' : '')}>
                  {g.dday >= 100 ? '상시' : `D-${g.dday}`}
                </span>
                <p>{g.agency} · {g.amount}</p>
                <div className="gov__tags">
                  <span className="gov__tag">{g.region}</span>
                  <span className="gov__tag">{g.type}</span>
                  <span className="gov__tag">{g.target}</span>
                </div>
                <button className="star gov__star" type="button" aria-pressed onClick={() => onToggleSave(g.id)}
                  aria-label={`${g.title} 저장 해제`}>★</button>
              </li>
            ))}
          </ul>
        )}
      </div>
    );
  }

  /* ===== 지출관리 ===== */
  const EXP_CATS = ['사무용품', '식대', '교통', '통신', '광고', '기타'];

  function ExpenseTracker() {
    const [items, setItems] = useState([
      { id: 1, date: '2025-10-04', name: '노트북 주변기기', amount: 89000, cat: '사무용품' },
      { id: 2, date: '2025-10-07', name: '거래처 미팅 식대', amount: 44000, cat: '식대' },
    ]);
    const [f, setF] = useState({ date: '', name: '', amount: '', cat: '사무용품' });
    const add = (e) => {
      e.preventDefault();
      if (!f.name.trim() || !f.amount) return;
      setItems((p) => [...p, {
        id: Date.now(),
        date: f.date || new Date().toISOString().slice(0, 10),
        name: f.name.trim(), amount: Number(f.amount), cat: f.cat,
      }]);
      setF({ date: '', name: '', amount: '', cat: '사무용품' });
    };
    const del = (id) => setItems((p) => p.filter((x) => x.id !== id));
    const total = items.reduce((s, x) => s + x.amount, 0);

    return (
      <div className="tool">
        <div className="tool__panel">
          <h2>지출관리 <span className="mp-tag" style={{ verticalAlign: 'middle' }}>BETA</span></h2>
          <form className="exp-form" onSubmit={add}>
            <input type="date" value={f.date} onChange={(e) => setF({ ...f, date: e.target.value })} aria-label="날짜" />
            <input type="text" placeholder="지출 항목" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} aria-label="항목" />
            <input type="number" min="0" placeholder="금액" value={f.amount} onChange={(e) => setF({ ...f, amount: e.target.value })} aria-label="금액" />
            <select value={f.cat} onChange={(e) => setF({ ...f, cat: e.target.value })} aria-label="분류">
              {EXP_CATS.map((c) => <option key={c}>{c}</option>)}
            </select>
            <button type="submit">추가</button>
          </form>
          <ul className="exp-list">
            {items.map((x) => (
              <li key={x.id}>
                <span className="u-num" style={{ color: 'var(--ink-soft)', fontSize: 12 }}>{x.date.slice(5)}</span>
                <span>{x.name}</span>
                <span className="exp-cat">{x.cat}</span>
                <span className="u-num">{x.amount.toLocaleString()}원</span>
                <button className="cal__ev-del" type="button" onClick={() => del(x.id)} aria-label="삭제">✕</button>
              </li>
            ))}
          </ul>
          <div className="exp-total"><span>합계</span><span className="u-num">{total.toLocaleString()}원</span></div>
          <p className="result__cite" style={{ marginTop: 10 }}>
            영수증 OCR·경비 인정 판정은 준비 중입니다. 지금은 직접 입력한 지출을 분류·합산합니다.
          </p>
        </div>
      </div>
    );
  }

  /* ===== 프로필 · 설정 ===== */
  function ProfileSettings({ user }) {
    const [form, setForm] = useState({
      name: user.name, email: user.email || '', biz: user.biz, region: user.region, age: '청년(만 15~34세)',
    });
    const [notif, setNotif] = useState({ tax: true, deadline: true, news: false });
    const [savedMsg, setSavedMsg] = useState(false);
    const upd = (k) => (e) => setForm({ ...form, [k]: e.target.value });
    const save = (e) => {
      e.preventDefault();
      setSavedMsg(true);
      setTimeout(() => setSavedMsg(false), 2500);
    };
    return (
      <div className="tool">
        <form className="tool__panel" onSubmit={save} style={{ marginBottom: 12 }}>
          <h2>프로필</h2>
          <div className="field-col">
            <label className="fld"><span>이름</span><input style={inputStyle} value={form.name} onChange={upd('name')} /></label>
            <label className="fld"><span>이메일</span><input style={inputStyle} type="email" value={form.email} onChange={upd('email')} /></label>
            <label className="fld"><span>업종</span><input style={inputStyle} value={form.biz} onChange={upd('biz')} /></label>
            <label className="fld"><span>사업장 지역</span><input style={inputStyle} value={form.region} onChange={upd('region')} /></label>
            <label className="fld"><span>대표자 연령</span>
              <select style={inputStyle} value={form.age} onChange={upd('age')}>
                <option>청년(만 15~34세)</option>
                <option>그 외</option>
              </select>
            </label>
          </div>
          <button type="submit" style={{
            marginTop: 14, padding: '10px 20px', border: 0, borderRadius: 11,
            background: 'linear-gradient(135deg, var(--blue), var(--blue-deep))', color: '#fff',
            fontSize: 13.5, fontWeight: 700, cursor: 'pointer',
          }}>저장</button>
          {savedMsg && <p className="pf-saved">저장되었습니다.</p>}
        </form>
        <div className="tool__panel">
          <h2>알림 설정</h2>
          {[['tax', '세금 신고 마감 알림'], ['deadline', '관심 공고 마감 3일 전 알림'], ['news', '창업 뉴스레터']].map(([k, label]) => (
            <div className="pf-toggle" key={k}>
              <span>{label}</span>
              <button type="button" className="pf-switch" aria-pressed={notif[k]} aria-label={label}
                onClick={() => setNotif((p) => ({ ...p, [k]: !p[k] }))} />
            </div>
          ))}
        </div>
      </div>
    );
  }

  function MyPage({ user, onHome, onLogout }) {
    const [menu, setMenu] = useState('home');
    const [saved, setSaved] = useState(() => new Set());
    const toggleSave = (id) =>
      setSaved((p) => {
        const n = new Set(p);
        n.has(id) ? n.delete(id) : n.add(id);
        return n;
      });
    const activeLabel = (MP_MENU.find((m) => m.key === menu) || {}).label || '';

    return (
      <div className="mp">
        <aside className="mp-side">
          <button className="mp-brand" type="button" onClick={onHome}>
            <span className="brand__mark" aria-hidden="true">ON</span>
            창업ON
          </button>
          <nav className="mp-nav" aria-label="마이페이지 메뉴">
            {MP_MENU.map((m, i) => {
              if (m.group) return <div className="mp-group" key={`g-${i}`}>{m.group}</div>;
              if (m.divider) return <div className="mp-side__div" key={`d-${i}`} />;
              return (
                <button
                  key={m.key}
                  type="button"
                  className={
                    'mp-link' +
                    (m.sub ? ' mp-link--sub' : '') +
                    (menu === m.key ? ' mp-link--active' : '')
                  }
                  aria-current={menu === m.key ? 'page' : undefined}
                  onClick={() => setMenu(m.key)}
                >
                  <span>{m.label}</span>
                  {m.tag && <span className="mp-tag">{m.tag}</span>}
                </button>
              );
            })}
          </nav>
        </aside>

        <main className="mp-main">
          <div className="mp-head">
            <div>
              <h1 className="mp-hello">안녕하세요, {user.name}님</h1>
              <p className="mp-basis">사업자 정보 기준 · {user.biz} · {user.region}</p>
            </div>
            <button className="mp-logout" type="button" onClick={onLogout}>로그아웃</button>
          </div>

          {menu === 'home' ? (
            <div className="mp-dash">
              <div className="mp-grid">
              <section className="mp-card">
                <div className="mp-card__head">
                  <h2 className="mp-card__title">세액감면 판정 요약</h2>
                  <span className="mp-card__tag">1티어</span>
                </div>
                <p className="mp-pct u-num">100%</p>
                <div className="mp-bar"><i style={{ width: '100%' }} /></div>
                <p className="mp-cite">
                  <span>근거 문서</span>
                  <span>조특법 제6조 외 <b>1건</b></span>
                </p>
              </section>

              <section className="mp-card">
                <div className="mp-card__head">
                  <h2 className="mp-card__title">다가오는 일정</h2>
                  <span className="mp-card__tag">세금 + 정책 통합</span>
                </div>
                <ul className="mp-rows">
                  {MP_SCHEDULE.map((s) => (
                    <li key={s.title}>
                      <span className="mp-rowlabel">{s.title}</span>
                      <span className="mp-rowval u-num">{s.when}</span>
                    </li>
                  ))}
                </ul>
              </section>

              <section className="mp-card">
                <div className="mp-card__head">
                  <h2 className="mp-card__title">추천 정책 Top 3</h2>
                  <span className="mp-card__tag">2티어</span>
                </div>
                <ul className="mp-rows">
                  {MP_RECO.map((r) => (
                    <li key={r.title}>
                      <button type="button" onClick={() => setMenu('explore')}>
                        <span className="mp-rowlabel">{r.title}</span>
                        <span className="mp-rowval u-num">{r.score}%</span>
                      </button>
                    </li>
                  ))}
                </ul>
              </section>

              <section className="mp-card">
                <div className="mp-card__head">
                  <h2 className="mp-card__title">최근 AI 상담</h2>
                  <span className="mp-card__tag">{MP_CONSULTS.length + 1}건</span>
                </div>
                <ul className="mp-rows">
                  {MP_CONSULTS.map((c) => (
                    <li key={c}>
                      <button type="button" onClick={() => setMenu('ai')}>
                        <span className="mp-consult">{c}</span>
                        <span className="mp-rowval">›</span>
                      </button>
                    </li>
                  ))}
                </ul>
              </section>
              </div>
              <MpCalendar />
            </div>
          ) : menu === 'ai' ? (
            <AiConsult user={user} />
          ) : menu === 'biz-type' ? (
            <BizTypeDiagnosis />
          ) : menu === 'tax-cut' ? (
            <TaxTool />
          ) : menu === 'tax-cal' ? (
            <MpCalendar full />
          ) : menu === 'explore' ? (
            <GovExplorer saved={saved} onToggleSave={toggleSave} />
          ) : menu === 'saved' ? (
            <SavedPolicies saved={saved} onToggleSave={toggleSave} onExplore={() => setMenu('explore')} />
          ) : menu === 'spend' ? (
            <ExpenseTracker />
          ) : menu === 'settings' ? (
            <ProfileSettings user={user} />
          ) : (
            <div className="mp-stub">
              <b>{activeLabel}</b> 화면은 준비 중입니다.
            </div>
          )}
        </main>
      </div>
    );
  }

  /* ---------- 상단 내비 ---------- */
  function Nav({ user, onLoginClick, onNavigate }) {
    const toggleTheme = useThemeToggle();
    const [menuOpen, setMenuOpen] = useState(false);
    const close = useCallback(() => setMenuOpen(false), []);

    return (
      <React.Fragment>
        <header className="nav">
          <div className="wrap nav__row">
            <button className="brand" type="button" onClick={() => onNavigate('home')}>
              <span className="brand__mark" aria-hidden="true">ON</span>
              창업ON
            </button>
            <span className="nav__spacer" />
            {user && <span className="nav__user"><b>{user.name}</b>님</span>}
            <button className="icon-btn" type="button" onClick={toggleTheme}
              aria-label="밝은 테마와 어두운 테마 전환">◐</button>
            <button className="hamburger" type="button"
              aria-haspopup="dialog" aria-expanded={menuOpen}
              aria-label="메뉴 열기" onClick={() => setMenuOpen(true)}>
              <span /><span /><span />
            </button>
          </div>
        </header>
        <MenuDrawer open={menuOpen} onClose={close} onNavigate={onNavigate}
          user={user} onAuth={onLoginClick} />
      </React.Fragment>
    );
  }

  /* ---------- 서브 페이지 ---------- */
  /* ===== 정부지원사업 탐색 ===== */
  const GOV_LISTINGS = [
    { id: 'g1', title: '예비창업패키지', agency: '창업진흥원', region: '전국', type: '자금', target: '예비', amount: '최대 1억 원', dday: 12 },
    { id: 'g2', title: '청년창업사관학교 15기', agency: '중소벤처기업진흥공단', region: '전국', type: '자금', target: '예비·초기', amount: '최대 1억 원', dday: 8 },
    { id: 'g3', title: '대전 청년창업 지원사업', agency: '대전창조경제혁신센터', region: '대전', type: '자금', target: '예비·초기', amount: '최대 3,000만 원', dday: 19 },
    { id: 'g4', title: '초기창업패키지', agency: '창업진흥원', region: '전국', type: '자금', target: '초기', amount: '최대 1억 원', dday: 26 },
    { id: 'g5', title: '1인 창조기업 마케팅 지원', agency: '소상공인시장진흥공단', region: '전국', type: '판로', target: '초기', amount: '최대 500만 원', dday: 37 },
    { id: 'g6', title: '대전 창업보육센터 입주기업 모집', agency: '대전테크노파크', region: '대전', type: '공간', target: '예비·초기', amount: '사무공간 · 보육', dday: 44 },
    { id: 'g7', title: '창업성장기술개발(디딤돌)', agency: '중소벤처기업부', region: '전국', type: 'R&D', target: '초기', amount: '최대 1.2억 원', dday: 53 },
    { id: 'g8', title: '재도전 성공패키지', agency: '창업진흥원', region: '전국', type: '자금', target: '재도전', amount: '최대 6,000만 원', dday: 15 },
    { id: 'g9', title: '대전 IT 스타트업 전문가 멘토링', agency: '정보통신산업진흥원', region: '대전', type: '멘토링', target: '초기', amount: '전문가 매칭', dday: 9 },
    { id: 'g10', title: '소상공인 첫걸음 컨설팅', agency: '소상공인시장진흥공단', region: '전국', type: '멘토링', target: '예비·초기', amount: '상시 접수', dday: 120 },
  ];
  const GOV_REGIONS = ['전체', '전국', '대전', '서울', '경기'];
  const GOV_TYPES = ['자금', '공간', '멘토링', '판로', 'R&D'];

  function GovExplorer({ saved: savedProp, onToggleSave } = {}) {
    const [region, setRegion] = useState('전체');
    const [types, setTypes] = useState([]);
    const [q, setQ] = useState('');
    const [savedLocal, setSavedLocal] = useState(() => new Set());
    const saved = savedProp || savedLocal;

    const toggleType = (t) =>
      setTypes((p) => (p.includes(t) ? p.filter((x) => x !== t) : [...p, t]));
    const toggleSave =
      onToggleSave ||
      ((id) =>
        setSavedLocal((p) => {
          const n = new Set(p);
          n.has(id) ? n.delete(id) : n.add(id);
          return n;
        }));

    // Backend: GET /api/announcements → 마감 남은 실제 공고 (DB)
    const { data: remote, source: listSrc } = useApi('/announcements?limit=60', null, (raw) =>
      (raw.announcements || []).map((x) => ({
        id: String(x.id),
        title: x.title,
        agency: x.industry || '기타',
        region: x.region || '전국',
        type: x.industry || '기타',
        target: x.target || '',
        amount: x.benefit || '',
        dday: x.dday === null || x.dday === undefined ? 999 : x.dday,
        url: x.sourceUrl,
      }))
    );
    const base = remote && remote.length ? remote : GOV_LISTINGS;
    const live = !!(remote && remote.length);

    const kw = q.trim().toLowerCase();
    const list = base
      .filter((g) => {
        const regionOk =
          region === '전체' ||
          (g.region || '').includes(region) ||
          (g.region || '') === '전국';
        const typeOk = types.length === 0 || types.some((t) => (g.type || '').includes(t));
        const textOk =
          !kw || `${g.title}${g.agency}${g.target}`.toLowerCase().includes(kw);
        return regionOk && typeOk && textOk;
      })
      .sort((a, b) => a.dday - b.dday);

    return (
      <div className="tool">
        <div className="tool__panel">
          <div className="gov__bar">
            <input
              className="gov__search"
              type="text"
              placeholder="공고명 · 기관 검색"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              aria-label="공고 검색"
            />
            <label className="fld" style={{ minWidth: 120 }}>
              <select value={region} onChange={(e) => setRegion(e.target.value)} aria-label="지역">
                {GOV_REGIONS.map((r) => (
                  <option key={r} value={r}>{r === '전체' ? '지역 전체' : r}</option>
                ))}
              </select>
            </label>
          </div>
          <div className="seg" role="group" aria-label="지원 유형">
            {GOV_TYPES.map((t) => (
              <button
                key={t}
                type="button"
                aria-pressed={types.includes(t)}
                onClick={() => toggleType(t)}
              >
                {t}
              </button>
            ))}
            {(types.length > 0 || region !== '전체' || q) && (
              <button type="button" onClick={() => { setTypes([]); setRegion('전체'); setQ(''); }}>
                초기화
              </button>
            )}
          </div>
        </div>

        <p className="gov__count">
          {list.length}건 · 저장 {saved.size}건
          {live ? ' · ● DB 실시간' : ' · ○ 데모 데이터'}
        </p>

        {list.length === 0 ? (
          <div className="gov__empty">조건에 맞는 공고가 없어요. 필터를 줄여보세요.</div>
        ) : (
          <ul className="gov__list">
            {list.map((g) => (
              <li className="gov__card" key={g.id}>
                <h3>{g.title}</h3>
                <span className={'gov__dday' + (g.dday <= 10 ? ' gov__dday--urgent' : '')}>
                  {g.dday >= 100 ? '상시' : `D-${g.dday}`}
                </span>
                <p>{g.agency} · {g.amount}</p>
                <div className="gov__tags">
                  <span className="gov__tag">{g.region}</span>
                  <span className="gov__tag">{g.type}</span>
                  <span className="gov__tag">{g.target}</span>
                </div>
                <button
                  className="star gov__star"
                  type="button"
                  aria-pressed={saved.has(g.id)}
                  aria-label={`${g.title} 관심 공고 저장`}
                  onClick={() => toggleSave(g.id)}
                >
                  {saved.has(g.id) ? '★' : '☆'}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    );
  }

  /* ===== 세금상담: 세액감면 판정 ===== */
  const TAX_SCHEDULE = [
    { when: '매월 10일', what: '원천세 신고·납부 (전월 급여 지급분)' },
    { when: '1월 25일', what: '부가가치세 2기 확정신고' },
    { when: '4월 25일', what: '부가가치세 1기 예정신고' },
    { when: '5월 31일', what: '종합소득세 확정신고' },
    { when: '7월 25일', what: '부가가치세 1기 확정신고' },
    { when: '10월 25일', what: '부가가치세 2기 예정신고' },
    { when: '11월 30일', what: '종합소득세 중간예납' },
  ];

  function TaxTool() {
    const [area, setArea] = useState('outside'); // outside | metro | declining
    const [youth, setYouth] = useState('yes'); // yes | no
    const [eligible, setEligible] = useState('yes'); // yes | no
    const [srv, setSrv] = useState(null); // Backend Rule Engine 판정 결과

    // Backend: POST /api/tax/tax-reduction/check → 서버 Rule Engine + 근거 조문(DB)
    useEffect(() => {
      let alive = true;
      const ctl = new AbortController();
      api
        .taxCheck(
          {
            region: area === 'metro' ? '서울특별시' : '대전광역시',
            age: youth === 'yes' ? 32 : 45,
            industry: eligible === 'yes' ? '정보통신업' : '부동산업',
          },
          { signal: ctl.signal }
        )
        .then((r) => alive && setSrv(r))
        .catch(() => alive && setSrv(null));
      return () => {
        alive = false;
        ctl.abort();
      };
    }, [area, youth, eligible]);

    let rate = 0;
    let note = '';
    if (eligible === 'no') {
      rate = 0;
      note = '일반음식점·부동산업 등 일부 업종은 창업중소기업 세액감면 대상에서 제외돼요. 업종코드로 대상 여부를 먼저 확인하세요.';
    } else if (area === 'declining') {
      rate = 100;
      note = '인구감소지역에서 창업한 중소기업은 최초 소득 발생 과세연도부터 5년간 100% 감면됩니다.';
    } else if (youth === 'yes' && area === 'outside') {
      rate = 100;
      note = '만 15~34세 청년이 수도권 과밀억제권역 밖에서 창업하면 5년간 소득세·법인세 100% 감면됩니다.';
    } else if (youth === 'yes' && area === 'metro') {
      rate = 50;
      note = '청년 창업이라도 수도권 과밀억제권역 안이면 5년간 50% 감면됩니다.';
    } else if (youth === 'no' && area === 'outside') {
      rate = 50;
      note = '청년 외 창업자가 수도권 과밀억제권역 밖에서 창업하면 5년간 50% 감면됩니다.';
    } else {
      rate = 0;
      note = '청년 외 창업자가 수도권 과밀억제권역 안에서 창업하면 일반적으로 창업 세액감면 대상이 아니에요. (연 수입금액 8,000만 원 이하 등 별도 요건은 추가 확인이 필요합니다.)';
    }

    return (
      <div className="tool">
        <div className="tool__panel">
          <h2>세액감면 판정</h2>
          <div className="field-col">
            <label className="fld">
              <span>창업 지역</span>
              <div className="seg">
                {[
                  ['outside', '수도권 과밀억제권역 밖'],
                  ['metro', '수도권 과밀억제권역 안'],
                  ['declining', '인구감소지역'],
                ].map(([v, l]) => (
                  <button key={v} type="button" aria-pressed={area === v} onClick={() => setArea(v)}>{l}</button>
                ))}
              </div>
            </label>
            <label className="fld">
              <span>대표자 연령</span>
              <div className="seg">
                <button type="button" aria-pressed={youth === 'yes'} onClick={() => setYouth('yes')}>청년 (만 15~34세)</button>
                <button type="button" aria-pressed={youth === 'no'} onClick={() => setYouth('no')}>그 외</button>
              </div>
            </label>
            <label className="fld">
              <span>감면 대상 업종</span>
              <div className="seg">
                <button type="button" aria-pressed={eligible === 'yes'} onClick={() => setEligible('yes')}>해당 (제조·정보통신 등)</button>
                <button type="button" aria-pressed={eligible === 'no'} onClick={() => setEligible('no')}>제외 업종</button>
              </div>
            </label>
          </div>

          <div className="result">
            <p className="result__label">예상 세액감면율</p>
            <div className="result__rate u-num">
              {rate}%{rate > 0 && <small>· 5년간</small>}
            </div>
            <p className="result__note">
              {note}
              {rate > 0 && ' 감면 기간은 최초 소득이 발생한 과세연도와 그 다음 4개 과세연도입니다.'}
            </p>
            <p className="result__cite">
              근거 · 조세특례제한법 제6조(창업중소기업 등에 대한 세액감면) · 실제 적용은 세무대리인 확인이 필요합니다.
            </p>

            {srv && srv.legalBasis && srv.legalBasis.length > 0 && (
              <div className="msg-src" style={{ maxWidth: 'none', marginTop: 12 }}>
                <b>
                  DB 근거 조문 {srv.legalBasis.length}건 · 서버 판정 {srv.rate}%
                  {srv.rate === rate ? ' (프론트 계산과 일치)' : ''}
                </b>
                {srv.legalBasis.map((s) => (
                  <a key={s.id} href={s.url || '#'} target="_blank" rel="noreferrer">
                    {s.lawName} · {s.title}
                  </a>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="tool__panel">
          <h2>주요 신고 일정</h2>
          <ul className="cal-list">
            {TAX_SCHEDULE.map((s) => (
              <li key={s.when}>
                <span>{s.what}</span>
                <b className="u-num">{s.when}</b>
              </li>
            ))}
          </ul>
        </div>
      </div>
    );
  }

  /* ===== 창업 로드맵 가이드 (AI 도움말 포함) ===== */
  /* 단계별로 연결되는 지원사업 (GOV_LISTINGS id) */
  const ROADMAP_PROGRAMS = {
    A: ['g10', 'g9'],
    B: ['g10'],
    C: ['g1', 'g2', 'g3'],
    D: ['g4', 'g8', 'g3'],
    E: ['g10'],
    F: ['g5'],
    Z: ['g7', 'g6'],
  };
  const progById = (id) => GOV_LISTINGS.find((g) => g.id === id);
  const ddayLabel = (g) => (g.dday >= 100 ? '상시' : `D-${g.dday}`);

  /* 프로필 기준 매칭 점수 + 이유 */
  function scoreProgram(g, u) {
    let s = 40;
    const why = [];
    if (u && u.region && g.region !== '전국' && u.region.includes(g.region)) {
      s += 30;
      why.push(`${g.region} 지역 사업`);
    } else if (g.region === '전국') {
      s += 18;
      why.push('전국 대상');
    }
    if (/예비|초기/.test(g.target)) {
      s += 18;
      why.push(`${g.target} 창업자 대상`);
    }
    if (g.dday >= 100) {
      s += 6;
      why.push('상시 접수');
    } else if (g.dday <= 30) {
      s += 12;
      why.push(`마감 D-${g.dday}`);
    }
    if (g.type === '자금') {
      s += 8;
      why.push('사업화 자금');
    }
    return { score: Math.min(99, s), why };
  }

  function RoadmapGuide({ user }) {
    const [active, setActive] = useState('A');
    const [done, setDone] = useState({});
    const [sampleFn, setSampleFn] = useState(undefined);
    const [aiText, setAiText] = useState('');
    const [aiBusy, setAiBusy] = useState(false);
    const [aiErr, setAiErr] = useState('');
    const [sumText, setSumText] = useState('');
    const [sumBusy, setSumBusy] = useState(false);
    const [sumErr, setSumErr] = useState('');
    const ctlRef = useRef(null);
    const sumCtlRef = useRef(null);

    useEffect(() => {
      let alive = true;
      (async () => {
        try {
          const s = window.claude && (await window.claude.use('sample'));
          if (alive) setSampleFn(() => s || null);
        } catch (e) {
          if (alive) setSampleFn(() => null);
        }
      })();
      return () => {
        alive = false;
        if (ctlRef.current) ctlRef.current.abort();
        if (sumCtlRef.current) sumCtlRef.current.abort();
      };
    }, []);

    useEffect(() => {
      setAiText('');
      setAiErr('');
    }, [active]);

    const step = ROADMAP.find((s) => s.k === active);
    const tasks = ROADMAP_TASKS[active] || [];
    const doneCount = tasks.filter((_, i) => done[`${active}:${i}`]).length;
    const stepPct = tasks.length ? Math.round((doneCount / tasks.length) * 100) : 0;
    const totalTasks = ROADMAP.reduce((n, s) => n + (ROADMAP_TASKS[s.k] || []).length, 0);
    const totalDone = Object.values(done).filter(Boolean).length;
    const overallPct = totalTasks ? Math.round((totalDone / totalTasks) * 100) : 0;

    const toggle = (i) =>
      setDone((d) => ({ ...d, [`${active}:${i}`]: !d[`${active}:${i}`] }));
    const stepDone = (k) => {
      const t = ROADMAP_TASKS[k] || [];
      return t.length > 0 && t.every((_, i) => done[`${k}:${i}`]);
    };

    /* 단계별 지원사업 / 완료 리포트용 매칭 */
    const stepProgs = (ROADMAP_PROGRAMS[active] || []).map(progById).filter(Boolean);
    const completedSteps = ROADMAP.filter((s) => stepDone(s.k));
    const allDone = overallPct === 100;
    const matches = [...new Set(Object.values(ROADMAP_PROGRAMS).flat())]
      .map(progById)
      .filter(Boolean)
      .map((g) => ({ g, ...scoreProgram(g, user) }))
      .sort((a, b) => b.score - a.score || a.g.dday - b.g.dday)
      .slice(0, 5);

    const askSummary = async () => {
      if (!sampleFn || sumBusy) return;
      setSumErr('');
      setSumBusy(true);
      setSumText('');
      const ctl = new AbortController();
      sumCtlRef.current = ctl;
      const prompt =
        '너는 창업 코치야. 아래 사용자가 창업 로드맵 7단계를 모두 마쳤어. ' +
        '이 사람이 지금 무엇을 어떤 순서로 신청해야 하는지 한국어로 정리해줘.\n' +
        '형식: (1) 한 줄 요약 (2) 신청 우선순위 3개 — "사업명 — 이유 — 준비서류 1~2개" (3) 세무 체크포인트 2개 ' +
        '(4) "⚠️ "로 시작하는 주의사항 1개. 각 줄은 짧게. 이 화면은 데모야.\n\n' +
        `사용자: ${(user && user.biz) || '정보통신업'} / ${(user && user.region) || '대전광역시'}\n` +
        `완료한 단계: ${completedSteps.map((s) => s.t).join(', ')}\n` +
        `매칭된 지원사업: ${matches.map((m) => `${m.g.title}(${m.g.agency}, ${m.g.amount}, ${ddayLabel(m.g)})`).join(' / ')}`;
      try {
        await sampleFn(prompt, {
          modelTier: 'quick',
          signal: ctl.signal,
          onText: ({ text }) => setSumText(text),
        });
      } catch (e) {
        const code = e && e.code;
        if (code !== 'cancelled') setSumErr(AI_ERR[code] || '응답을 불러오지 못했어요.');
        if (e && e.text) setSumText(e.text);
      } finally {
        setSumBusy(false);
        sumCtlRef.current = null;
      }
    };

    const askAi = async () => {
      if (!sampleFn || aiBusy) return;
      setAiErr('');
      setAiBusy(true);
      setAiText('');
      const ctl = new AbortController();
      ctlRef.current = ctl;
      const prompt =
        '너는 창업 로드맵 코치야. 사용자는 대전광역시에서 정보통신업으로 창업을 준비 중인 초기 창업자야. ' +
        `아래 "${step.phase} · ${step.t}" 단계에서 이 사용자가 지금 해야 할 일을 실행 순서대로 4~6개의 짧은 체크리스트로 한국어로 알려줘. ` +
        '각 항목은 한 줄, 담당 기관이나 서류명이 있으면 괄호로 덧붙여. 마지막 줄에는 이 단계에서 가장 흔한 실수 1가지를 "⚠️ "로 시작해 한 문장으로 알려줘. 이 화면은 데모야.\n\n' +
        `참고할 기본 작업: ${tasks.join(', ')}`;
      try {
        await sampleFn(prompt, {
          modelTier: 'quick',
          signal: ctl.signal,
          onText: ({ text }) => setAiText(text),
        });
      } catch (e) {
        const code = e && e.code;
        if (code !== 'cancelled') setAiErr(AI_ERR[code] || '응답을 불러오지 못했어요.');
        if (e && e.text) setAiText(e.text);
      } finally {
        setAiBusy(false);
        ctlRef.current = null;
      }
    };

    return (
      <div className="tool" style={{ maxWidth: 960 }}>
        <div className="tool__panel" style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 8 }}>
            <h2 style={{ margin: 0 }}>전체 진행률</h2>
            <b className="u-num" style={{ fontSize: 15, color: 'var(--blue-deep)' }}>{overallPct}%</b>
          </div>
          <div className="rg__progress"><i style={{ width: overallPct + '%' }} /></div>
          <p style={{ margin: 0, fontSize: 12, color: 'var(--ink-faint)' }}>
            {totalDone} / {totalTasks} 작업 완료 · 완료 단계 {completedSteps.length} / {ROADMAP.length}
          </p>
        </div>

        {/* 완료 리포트 */}
        {allDone ? (
          <div className="rg__report">
            <h2>🎉 로드맵 완료 · {(user && user.name) || '창업자'}님 맞춤 리포트</h2>
            <p>
              {(user && user.biz) || '정보통신업'} · {(user && user.region) || '대전광역시'} 기준으로,
              완료한 {completedSteps.length}개 단계에서 연결된 지원사업을 매칭했어요.
            </p>

            <h3 className="rg__secttl">신청 추천 지원사업 Top {matches.length}</h3>
            {matches.map((m, i) => (
              <div className="rg__match" key={m.g.id}>
                <span className="rg__rank">{i + 1}</span>
                <b>{m.g.title}</b>
                <span className="rg__score u-num">{m.score}%</span>
                <div className="rg__why">
                  <span>{m.g.agency}</span>
                  <span>{m.g.amount}</span>
                  <span>{ddayLabel(m.g)}</span>
                  {m.why.map((w) => <span key={w}>{w}</span>)}
                </div>
              </div>
            ))}

            <h3 className="rg__secttl">세무 체크포인트</h3>
            <ul className="rg__next">
              <li>
                창업중소기업 세액감면(조특법 제6조) — {(user && user.region) || '대전광역시'}는 수도권 과밀억제권역
                밖이라 청년 창업 시 <b>5년간 100% 감면</b> 대상이 될 수 있어요. 종합소득세 신고 때 「세액감면신청서」 동시 제출.
              </li>
              <li>부가가치세 신고(1·7월 확정 / 4·10월 예정)와 지원사업 정산 일정이 겹치지 않게 캘린더에 등록하세요.</li>
            </ul>

            <h3 className="rg__secttl">다음 액션</h3>
            <ul className="rg__next">
              <li>1순위 <b>{matches[0] && matches[0].g.title}</b> 공고문을 「공고문 AI 분석」에서 요건·서류로 구조화하기</li>
              <li>사업계획서(PSST) 초안 작성 후 마감 3일 전 제출 목표로 캘린더 등록</li>
              <li>「AI 세무 Assistant」에서 세액감면 대상 여부를 근거 조문과 함께 최종 확인</li>
            </ul>

            {sampleFn === null ? (
              <p className="rg__ai rg__ai--muted">AI 정리는 claude.ai에서 열면 사용할 수 있어요.</p>
            ) : (
              <div style={{ marginTop: 16 }}>
                {sumBusy ? (
                  <button type="button" className="btn btn--ghost"
                    onClick={() => sumCtlRef.current && sumCtlRef.current.abort()}>생성 중지</button>
                ) : (
                  <button type="button" className="btn btn--primary" disabled={!sampleFn} onClick={askSummary}>
                    AI로 실행 계획 정리받기
                  </button>
                )}
                {(sumText || sumBusy) && <div className="rg__ai">{sumText || '정리하는 중…'}</div>}
                {sumErr && <p className="ai__err" style={{ padding: '8px 0 0' }}>{sumErr}</p>}
              </div>
            )}
          </div>
        ) : (
          <div className="rg__report rg__report--locked">
            <h2>맞춤 지원사업 리포트</h2>
            <p style={{ margin: 0 }}>
              7단계 체크리스트를 모두 완료하면, 완료 내용과 내 프로필을 기준으로
              <b> 신청할 지원사업 · 세무 체크포인트 · 다음 액션</b>을 정리해 드려요.
              (현재 {totalDone} / {totalTasks} · {totalTasks - totalDone}개 남음)
            </p>
          </div>
        )}

        <div className="rg">
          <nav className="rg__nav" aria-label="창업 단계">
            {ROADMAP.map((s) => (
              <button
                key={s.k}
                type="button"
                className={
                  'rg__navitem' +
                  (s.k === active ? ' rg__navitem--active' : '') +
                  (stepDone(s.k) ? ' rg__navitem--done' : '')
                }
                onClick={() => setActive(s.k)}
              >
                <span className="rg__navk">{stepDone(s.k) ? '✓' : s.k}</span>
                <span>{s.t}</span>
              </button>
            ))}
          </nav>

          <div className="rg__panel">
            <span className="rg__phase">{step.phase}</span>
            <h3 className="rg__title">{step.k}. {step.t}</h3>
            <p className="rg__desc">{step.d}</p>
            <div className="rg__progress"><i style={{ width: stepPct + '%' }} /></div>
            <ul className="rg__tasks">
              {tasks.map((t, i) => {
                const d = !!done[`${active}:${i}`];
                return (
                  <li
                    key={i}
                    className={'rg__task' + (d ? ' rg__task--done' : '')}
                    onClick={() => toggle(i)}
                  >
                    <input
                      type="checkbox"
                      checked={d}
                      onChange={() => toggle(i)}
                      onClick={(e) => e.stopPropagation()}
                    />
                    <span>{t}</span>
                  </li>
                );
              })}
            </ul>

            <div className="rg__progs">
              <h4>이 단계에서 활용할 수 있는 지원사업</h4>
              {stepProgs.length === 0 ? (
                <p className="rg__none">이 단계에 직접 연결되는 공고는 없어요. 세무·행정 절차 위주 단계입니다.</p>
              ) : (
                stepProgs.map((g) => (
                  <div className="rg__prog" key={g.id}>
                    <b>{g.title}</b>
                    <em className={g.dday <= 10 ? 'is-urgent' : ''}>{ddayLabel(g)}</em>
                    <span>{g.agency} · {g.amount} · {g.region}</span>
                  </div>
                ))
              )}
            </div>

            {sampleFn === null ? (
              <p className="rg__ai rg__ai--muted">
                이 화면에서는 AI 도움말을 사용할 수 없어요. claude.ai에서 열면 활성화됩니다.
              </p>
            ) : (
              <React.Fragment>
                {aiBusy ? (
                  <button type="button" className="btn btn--ghost"
                    onClick={() => ctlRef.current && ctlRef.current.abort()}>
                    생성 중지
                  </button>
                ) : (
                  <button type="button" className="btn btn--primary" disabled={!sampleFn} onClick={askAi}>
                    이 단계, AI에게 물어보기
                  </button>
                )}
                {(aiText || aiBusy) && <div className="rg__ai">{aiText || '생각 중…'}</div>}
                {aiErr && <p className="ai__err" style={{ padding: '8px 0 0' }}>{aiErr}</p>}
              </React.Fragment>
            )}
          </div>
        </div>
      </div>
    );
  }

  /* ===== AI 세무 Assistant (예시 대화 + 실시간) ===== */
  const TAX_RULES =
    '너는 "창업ON"의 AI 세무 Assistant야. 청년·1인 창업자의 세무를 돕는다. ' +
    '주요 영역: 청년창업 세액감면 자동 판정(조세특례제한법 제6조), 사업자 유형(개인/법인, 간이/일반), ' +
    '부가가치세·종합소득세 신고 일정, 경비처리·절세. ' +
    '한국어로 간결하게(필요하면 불릿) 답하고, 판정·수치에는 근거(법령 조문명 등)를 함께 제시해. ' +
    '확정 판단이 필요하면 관할 세무서·세무대리인 확인을 권해. 이 화면은 데모다.';

  const TAX_SEED = [
    { role: 'user', content: '2024년 3월에 대전에서 만 32세에 온라인 코딩 교육 서비스로 개인사업자를 냈어요. 청년창업 세액감면 받을 수 있나요?' },
    { role: 'assistant', content: '요건을 대부분 충족합니다.\n• 나이: 창업 당시 만 15~34세 → 청년 요건 O\n• 지역: 대전은 수도권 과밀억제권역 밖 → 감면율 100%\n• 업종: 정보통신업·교육서비스업은 조특법 제6조 감면 대상 업종\n→ 최초로 소득이 발생한 과세연도부터 5년간 소득세 100% 감면(조특법 제6조 ①). 종합소득세 신고 때 「세액감면신청서」를 함께 제출해야 적용됩니다.' },
    { role: 'user', content: '감면받으면 부가가치세도 안 내나요?' },
    { role: 'assistant', content: '아니요. 창업중소기업 세액감면은 소득세·법인세에만 적용돼요. 부가가치세는 별도로, 일반과세자라면 1월·7월 확정신고, 4월·10월 예정신고를 그대로 하셔야 합니다.' },
    { role: 'user', content: '업무용 노트북이랑 강의실 인테리어 비용도 경비처리 되나요?' },
    { role: 'assistant', content: '업무용이면 둘 다 필요경비로 인정됩니다. 노트북 등 100만 원 이상 자산은 감가상각(중소기업 즉시상각 특례로 당해 전액 비용화도 가능), 인테리어는 시설장치로 감가상각해요. 세금계산서·카드전표 등 적격증빙을 꼭 보관하세요.' },
  ];

  const TAX_CHIPS = [
    '창업 당시 만 35세였는데 세액감면 되나요?',
    '간이과세자와 일반과세자 차이 알려줘',
    '올해 종합소득세 신고는 언제 하나요?',
    '차량 리스료도 경비처리 되나요?',
  ];

  function TaxAssistantPage({ user }) {
    return (
      <div className="tool" style={{ maxWidth: 980 }}>
        <AiConsult
          large
          user={user || { biz: '정보통신업', region: '대전광역시' }}
          rules={TAX_RULES}
          seed={TAX_SEED}
          suggestions={TAX_CHIPS}
          title="AI 세무 Assistant"
        />
        <div style={{ marginTop: 16 }}>
          <TaxTool />
        </div>
      </div>
    );
  }

  /* ===== 지원사업 공고문 AI 분석·구조화 ===== */
  const ANNC_SAMPLES = [
    {
      id: 'pre',
      label: '예비창업패키지',
      text:
        '2025년 예비창업패키지 창업사업화 지원 공고\n\n' +
        '1. 지원대상: 공고일 기준 사업자등록(개인·법인) 이력이 없는 만 39세 이하 예비창업자\n' +
        '2. 지원내용\n - 사업화 자금: 최대 1억 원(평균 5천만 원 내외), 총사업비의 70% 이내\n - 창업교육 및 전담멘토링 제공\n' +
        '3. 신청기간: 2025. 3. 10.(월) 10:00 ~ 3. 31.(월) 16:00\n' +
        '4. 신청방법: K-Startup 누리집(www.k-startup.go.kr) 온라인 접수\n' +
        '5. 제출서류: 사업신청서, 사업계획서(PSST 양식), 대표자 신분증 사본, 개인정보 수집·이용 동의서\n' +
        '6. 유의사항\n - 접수 마감 직전 신청 폭주로 인한 접속 지연 대비 사전 제출 권장\n - 국세·지방세 체납 시 선정 취소\n - 타 정부 창업사업화 지원사업과 중복 수혜 불가',
    },
    {
      id: 'dj',
      label: '대전 청년창업 지원',
      text:
        '2025년 대전형 청년창업 지원사업 참여기업 모집\n\n' +
        '□ 모집대상: 대전에 사업장을 둔(예정 포함) 만 19~39세, 창업 3년 이내 청년기업\n' +
        '□ 지원규모: 기업당 최대 3,000만 원(자부담 20%), 30개사 내외\n' +
        '□ 지원항목: 시제품 제작, 마케팅, 지식재산권 출원, 임차료(월 최대 50만 원)\n' +
        '□ 접수기간: 2025. 4. 1.(화) ~ 4. 21.(월) 18:00까지\n' +
        '□ 접수방법: 대전창조경제혁신센터 이메일 접수(startup@dcei.kr)\n' +
        '□ 구비서류: 참여신청서, 사업계획서, 사업자등록증(해당 시), 주민등록초본, 청년 확인 서류\n' +
        '□ 참고사항\n - 대전 외 지역 사업자는 선정 후 3개월 이내 대전 이전 조건\n - 유흥·사행성 업종 및 부동산업 제외\n - 최종 선정 후 협약 미체결 시 지원 포기로 간주',
    },
  ];

  const ANNC_FALLBACK = {
    pre: {
      target: '사업자등록 이력이 없는 만 39세 이하 예비창업자 (개인·법인 공통)',
      benefit: '사업화 자금 최대 1억 원(평균 약 5천만 원, 총사업비의 70% 이내) + 창업교육·전담멘토링',
      period: '2025. 3. 10. 10:00 ~ 2025. 3. 31. 16:00',
      method: 'K-Startup 누리집(www.k-startup.go.kr) 온라인 접수',
      documents: ['사업신청서', '사업계획서(PSST 양식)', '대표자 신분증 사본', '개인정보 수집·이용 동의서'],
      notes: ['마감 직전 접속 지연 대비 사전 제출 권장', '국세·지방세 체납 시 선정 취소', '타 정부 창업사업화 지원사업과 중복 수혜 불가'],
      source: '2025년 예비창업패키지 창업사업화 지원 공고 · K-Startup',
    },
    dj: {
      target: '대전 소재(예정 포함) 만 19~39세, 창업 3년 이내 청년기업',
      benefit: '기업당 최대 3,000만 원(자부담 20%) · 시제품 제작, 마케팅, IP 출원, 임차료(월 최대 50만 원)',
      period: '2025. 4. 1. ~ 2025. 4. 21. 18:00',
      method: '대전창조경제혁신센터 이메일 접수(startup@dcei.kr)',
      documents: ['참여신청서', '사업계획서', '사업자등록증(해당 시)', '주민등록초본', '청년 확인 서류'],
      notes: ['대전 외 사업자는 선정 후 3개월 이내 대전 이전 조건', '유흥·사행성 업종 및 부동산업 제외', '협약 미체결 시 지원 포기로 간주'],
      source: '2025년 대전형 청년창업 지원사업 모집 공고 · 대전창조경제혁신센터',
    },
  };

  function AnnouncementAnalyzer() {
    const [text, setText] = useState('');
    const [result, setResult] = useState(null);
    const [busy, setBusy] = useState(false);
    const [err, setErr] = useState('');
    const [usedAi, setUsedAi] = useState(false);
    const [sampleFn, setSampleFn] = useState(undefined);
    const ctlRef = useRef(null);
    const lastSampleId = useRef(null);

    useEffect(() => {
      let alive = true;
      (async () => {
        try {
          const s = window.claude && (await window.claude.use('sample'));
          if (alive) setSampleFn(() => s || null);
        } catch (e) {
          if (alive) setSampleFn(() => null);
        }
      })();
      return () => {
        alive = false;
        if (ctlRef.current) ctlRef.current.abort();
      };
    }, []);

    const loadSample = (s) => {
      setText(s.text);
      setResult(null);
      setErr('');
      lastSampleId.current = s.id;
    };

    const analyze = async () => {
      const body = text.trim();
      if (!body || busy) return;
      setErr('');
      setResult(null);
      setBusy(true);

      if (!sampleFn) {
        const fb = lastSampleId.current && ANNC_FALLBACK[lastSampleId.current];
        setTimeout(() => {
          setBusy(false);
          if (fb) {
            setResult(fb);
            setUsedAi(false);
          } else {
            setErr('이 화면에서는 실시간 AI 분석을 사용할 수 없어요. 위 예시 공고문 버튼을 눌러 구조화 결과를 확인해 보세요.');
          }
        }, 300);
        return;
      }

      const ctl = new AbortController();
      ctlRef.current = ctl;
      const prompt =
        '아래 정부·지자체 지원사업 공고문을 분석해 다음 JSON 형태로만 답해.\n' +
        '{"target": string, "benefit": string, "period": string, "method": string, "documents": string[], "notes": string[], "source": string}\n' +
        '- 공고문에 적힌 내용을 근거로 한국어로 간결하게. 없으면 "명시 없음".\n' +
        '- documents(제출 서류), notes(유의사항)는 항목별 배열. source는 공고명과 발행 기관.\n\n[공고문]\n' +
        body;
      try {
        const data = await sampleFn.json(prompt, { modelTier: 'quick', signal: ctl.signal });
        setResult(data);
        setUsedAi(true);
      } catch (e) {
        const code = e && e.code;
        if (code !== 'cancelled') {
          setErr(
            AI_ERR[code] ||
              (code === 'invalid_json'
                ? 'AI 응답을 구조화하지 못했어요. 다시 시도해 주세요.'
                : '분석에 실패했어요. 잠시 후 다시 시도해 주세요.')
          );
        }
      } finally {
        setBusy(false);
        ctlRef.current = null;
      }
    };

    const cell = (label, value, wide) => (
      <div className={'az__cell' + (wide ? ' az__cell--wide' : '')}>
        <h4>{label}</h4>
        {Array.isArray(value) ? (
          <ul>
            {(value.length ? value : ['명시 없음']).map((x, i) => (
              <li key={i}>{String(x)}</li>
            ))}
          </ul>
        ) : (
          <p>{value || '명시 없음'}</p>
        )}
      </div>
    );

    return (
      <div className="tool az" style={{ maxWidth: 900 }}>
        <div className="tool__panel">
          <h2>공고문 붙여넣기</h2>
          <div className="az__samples">
            {ANNC_SAMPLES.map((s) => (
              <button key={s.id} type="button" className="ai__chip" onClick={() => loadSample(s)}>
                {s.label} 예시
              </button>
            ))}
          </div>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="지원사업 공고문 전문을 붙여넣으세요."
            aria-label="공고문 입력"
          />
          <div className="az__actions">
            {busy ? (
              <button type="button" className="btn btn--ghost" onClick={() => ctlRef.current && ctlRef.current.abort()}>
                중지
              </button>
            ) : (
              <button type="button" className="btn btn--primary" onClick={analyze} disabled={!text.trim()}>
                AI로 구조화 분석
              </button>
            )}
            <span style={{ fontSize: 12, color: 'var(--ink-faint)' }}>
              {sampleFn === undefined ? '연결 중…' : sampleFn ? 'AI 분석 가능' : '예시 공고문만 분석 가능'}
            </span>
          </div>
          {err && <p className="ai__err" style={{ padding: '10px 0 0' }}>{err}</p>}
        </div>

        {busy && <div className="gov__empty" style={{ marginTop: 16 }}>공고문 분석 중…</div>}

        {result && (
          <div className="tool__panel" style={{ marginTop: 16 }}>
            <h2>구조화 결과{usedAi ? '' : ' (예시)'}</h2>
            <div className="az__grid">
              {cell('지원 대상', result.target, true)}
              {cell('지원 내용 · 금액', result.benefit, true)}
              {cell('신청 기간', result.period)}
              {cell('신청 방법', result.method)}
              {cell('제출 서류', result.documents)}
              {cell('유의사항', result.notes)}
            </div>
            <p className="az__src">
              출처 · {result.source || '공고문 원문'} · {usedAi ? 'AI 구조화 결과, 원문 대조 필요' : '데모 예시 데이터'}
            </p>
          </div>
        )}
      </div>
    );
  }

  function SubPage({ pageKey, user, onHome, onLoginClick, onNavigate }) {
    const meta =
      {
        roadmap: { title: '창업 로드맵', lead: '단계별 할 일을 체크하고, 각 단계에서 무엇을 해야 하는지 AI에게 물어보세요.' },
        tax: { title: 'AI 세무 Assistant', lead: '청년창업 세액감면 자동 판정, 신고 일정, 경비처리 등 세무 질문에 근거와 함께 답합니다.' },
        gov: { title: '지원사업 공고문 AI 분석', lead: '공고문을 붙여넣으면 지원대상 · 내용 · 기간 · 서류 · 유의사항으로 구조화해 드려요.' },
        ai: { title: 'AI 상담', lead: '세무 · 창업 질문에 근거와 함께 실시간으로 답합니다.' },
      }[pageKey] || { title: '창업ON', lead: '' };

    return (
      <React.Fragment>
        <Nav user={user} onLoginClick={onLoginClick} onNavigate={onNavigate} />
        <div className="fp">
          <div className="fp__head">
            <div className="fp__head-in">
              <button className="fp__back" type="button" onClick={onHome}>← 홈으로</button>
              <h1 className="fp__title">{meta.title}</h1>
              <p className="fp__lead">{meta.lead}</p>
            </div>
          </div>
          <div className="fp__body">
            {pageKey === 'roadmap' && <RoadmapGuide user={user} />}
            {pageKey === 'gov' && <AnnouncementAnalyzer />}
            {pageKey === 'tax' && <TaxAssistantPage user={user} />}
            {pageKey === 'ai' && (
              <AiConsult user={user || { biz: '정보통신업', region: '대전광역시' }} />
            )}
          </div>
        </div>
        <footer className="foot">
          <div className="wrap">창업ON · 화면의 수치와 공고는 데모용 예시 데이터입니다.</div>
        </footer>
      </React.Fragment>
    );
  }

  /* ---------- 홈: Hero ---------- */
  function DeadlinePanel() {
    // Backend: GET /api/announcements → 마감 임박 공고 (DB의 실제 공고)
    const { data: deadlines, source } = useApi('/announcements?limit=4', DEADLINES, (raw) =>
      (raw.announcements || []).slice(0, 4).map((x) => ({
        id: String(x.id),
        dday: x.dday === null || x.dday === undefined ? '상시' : `D-${x.dday}`,
        tone: x.dday <= 7 ? 'urgent' : x.dday <= 30 ? 'soon' : 'normal',
        title: x.title,
        meta: [x.region, x.industry, x.benefit].filter(Boolean).join(' · ').slice(0, 60),
        url: x.sourceUrl,
      }))
    );

    const [saved, setSaved] = useState(() => new Set());
    const toggle = (id) =>
      setSaved((prev) => {
        const next = new Set(prev);
        next.has(id) ? next.delete(id) : next.add(id);
        return next;
      });

    return (
      <aside className="panel" aria-labelledby="panel-title">
        <div className="panel__head">
          <h2 id="panel-title" className="panel__title">마감 임박 공고</h2>
          <span className="panel__more">전체 보기</span>
        </div>
        <ul className="deadlines">
          {deadlines.map((item) => (
            <li key={item.id} className="deadline">
              <span className={`deadline__dday u-num is-${item.tone}`}>{item.dday}</span>
              <div>
                <p className="deadline__title">{item.title}</p>
                <p className="deadline__meta">{item.meta}</p>
              </div>
              <button className="star" type="button" aria-pressed={saved.has(item.id)}
                aria-label={`${item.title} 관심 공고 저장`} onClick={() => toggle(item.id)}>
                {saved.has(item.id) ? '★' : '☆'}
              </button>
            </li>
          ))}
        </ul>
        <p className="panel__foot">
          {saved.size > 0
            ? `관심 공고 ${saved.size}건 저장됨 · 마감 3일 전 알림을 보내드려요`
            : '★ 를 눌러 관심 공고를 저장하면 마감 알림을 받아요'}
        </p>
      </aside>
    );
  }

  function Hero({ onNavigate }) {
    // Backend: GET /api/stats → 실제 모집 중 공고 수
    const { data: stats, source: statsSrc } = useApi('/stats', null, (raw) => raw);
    const total = (stats && stats.openAnnouncements) || 1842;
    const count = useCountUp(total, true);
    let wi = 0;
    return (
      <section className="hero" id="top">
        <div className="glow glow--blue" aria-hidden="true" />
        <div className="glow glow--violet" aria-hidden="true" />
        <div className="wrap hero__inner">
          <div>
            <p className="badge">
              <span className="badge__dot" aria-hidden="true" />
              매일 09:00 자동 갱신
            </p>
            <p className="figure u-num">
              {count.toLocaleString()}
              <span className="figure__unit">건 모집 중</span>
            </p>
            <h1 className="title">
              {HERO_TITLE.map((line, li) => (
                <React.Fragment key={li}>
                  {line.map((w) => (
                    <span className="w" style={{ '--i': wi++ }} key={w + wi}>
                      {w}
                      {' '}
                    </span>
                  ))}
                  {li === 0 && <br />}
                </React.Fragment>
              ))}
            </h1>
            <p className="lede">
              중앙부처 · 지자체 · 공공기관 공고를 모아 내 조건에 맞는 것만 골라
              드립니다. 세액 감면 대상 여부와 신고 일정까지 함께요.
            </p>
            <div className="hero__actions">
              <a className="btn btn--primary btn--lg" href="#onboarding">내 조건으로 찾기</a>
              <button className="btn btn--ghost btn--lg" type="button" onClick={() => onNavigate('roadmap')}>
                창업 로드맵 보기
              </button>
            </div>
            <dl className="stats">
              <div className="stat">
                <dt className="stat__label">수집 정책</dt>
                <dd className="stat__value u-num">
                  {stats ? `${stats.policies.toLocaleString()}건` : '2,907건'}
                </dd>
              </div>
              <div className="stat">
                <dt className="stat__label">세법 조문</dt>
                <dd className="stat__value u-num">
                  {stats ? `${stats.taxDocuments.toLocaleString()}건` : '4,459건'}
                </dd>
              </div>
              <div className="stat">
                <dt className="stat__label">최대 세액 감면</dt>
                <dd className="stat__value stat__value--pos u-num">
                  {stats ? `${stats.maxReductionRate}%` : '100%'}
                </dd>
              </div>
            </dl>
            <p style={{ marginTop: 14, fontSize: 11.5, color: 'var(--ink-faint)' }}>
              {statsSrc === 'api'
                ? '● 실시간 DB 연동 중 (Backend :8000 → Postgres)'
                : '○ 데모 데이터 (Backend 미실행 — cd Backend && uv run uvicorn main:app --port 8000)'}
            </p>
          </div>
          <DeadlinePanel />
        </div>
      </section>
    );
  }

  /* ---------- 홈 2: 창업 일정 달력 ---------- */
  /** Backend 의 /api/calendar 응답을 { 'YYYY-MM-DD': [{type,title,note}] } 로 변환 */
  function eventsByDate(raw) {
    const map = {};
    (raw.events || []).forEach((e) => {
      if (!e.date) return;
      (map[e.date] = map[e.date] || []).push({
        type: e.type === 'tax' ? 'tax' : 'policy',
        title: e.title,
        note: e.note || '',
      });
    });
    return map;
  }

  /** 홈 캘린더는 전부가 아니라 "중요 일정"만: 세금 신고일 전부 + 가까운 지원사업 마감 몇 개 */
  function pickImportant(map, maxPolicy = 5) {
    const out = {};
    const policyItems = [];
    Object.entries(map || {}).forEach(([date, arr]) => {
      const tax = arr.filter((e) => e.type === 'tax');
      if (tax.length) out[date] = tax.slice(0, 2);
      arr
        .filter((e) => e.type === 'policy')
        .forEach((e) => policyItems.push({ date, e }));
    });
    policyItems
      .sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : 0))
      .slice(0, maxPolicy)
      .forEach(({ date, e }) => {
        (out[date] = out[date] || []).push(e);
      });
    return out;
  }

  function Calendar() {
    const today = new Date();
    const todayKey = `${today.getFullYear()}-${pad2(today.getMonth() + 1)}-${pad2(today.getDate())}`;
    const [cur, setCur] = useState({ y: today.getFullYear(), m: today.getMonth() });
    const [sel, setSel] = useState(todayKey);

    // Backend: GET /api/calendar?year&month → 세금 신고일 + 지원사업 마감일 통합
    const { data: rawEvents } = useApi(
      `/calendar?year=${cur.y}&month=${cur.m + 1}&limit=200`,
      CAL_EVENTS,
      eventsByDate
    );
    // 홈에서는 모든 공고 마감이 아니라 "중요 일정"만 표시 (전체는 마이페이지 → 세금 일정)
    const events = pickImportant(rawEvents);

    const startDow = new Date(cur.y, cur.m, 1).getDay();
    const daysInMonth = new Date(cur.y, cur.m + 1, 0).getDate();
    const cells = [];
    for (let i = 0; i < startDow; i++) cells.push(null);
    for (let d = 1; d <= daysInMonth; d++) cells.push(d);
    while (cells.length % 7 !== 0) cells.push(null);

    const monthPrefix = `${cur.y}-${pad2(cur.m + 1)}`;
    const monthCount = Object.keys(events).filter((k) => k.startsWith(monthPrefix)).length;
    const shift = (delta) => {
      const nd = new Date(cur.y, cur.m + delta, 1);
      setCur({ y: nd.getFullYear(), m: nd.getMonth() });
    };
    const selEvents = events[sel] || [];
    const [sy, sm, sd] = sel.split('-').map(Number);
    const selLabel = `${sm}월 ${sd}일 (${WEEKDAYS[new Date(sy, sm - 1, sd).getDay()]})`;

    return (
      <div className="cal" role="group" aria-label="창업 일정 달력">
        <div className="cal__head">
          <h3 className="cal__title">창업 일정</h3>
          <div className="cal__nav">
            <button type="button" onClick={() => shift(-1)} aria-label="이전 달">‹</button>
            <span className="cal__month">{cur.y}.{pad2(cur.m + 1)}</span>
            <button type="button" onClick={() => shift(1)} aria-label="다음 달">›</button>
          </div>
        </div>
        <p className="cal__sub">
          이번 달 주요 일정 {monthCount}건 · 전체 일정은 마이페이지에서 확인하세요
        </p>
        <div className="cal__grid">
          {WEEKDAYS.map((w, i) => (
            <div key={w} className={'cal__dow' + (i === 0 ? ' cal__dow--sun' : '')}>{w}</div>
          ))}
          {cells.map((d, i) => {
            if (!d) return <div key={`e${i}`} className="cal__day cal__day--out" />;
            const k = dayKey(cur.y, cur.m, d);
            const types = [...new Set((events[k] || []).map((e) => e.type))];
            const isSel = k === sel;
            return (
              <button
                key={k}
                type="button"
                className={
                  'cal__day' +
                  (isSel ? ' cal__day--sel' : '') +
                  (k === todayKey && !isSel ? ' cal__day--today' : '')
                }
                aria-pressed={isSel}
                onClick={() => setSel(k)}
              >
                {d}
                {types.length > 0 && (
                  <span className="cal__dot">
                    {types.map((t) => <i key={t} className={t === 'tax' ? 't-tax' : 't-policy'} />)}
                  </span>
                )}
              </button>
            );
          })}
        </div>
        <div className="cal__legend">
          <span><i className="t-tax" /> 세금 신고</span>
          <span><i className="t-policy" /> 지원사업</span>
        </div>
        <div className="cal__events">
          <h4>{selLabel} 일정</h4>
          {selEvents.length === 0 ? (
            <p className="cal__empty">등록된 일정이 없어요.</p>
          ) : (
            selEvents.map((e) => (
              <div key={e.title} className="cal__ev">
                <i className={e.type === 'tax' ? 't-tax' : 't-policy'} />
                <div>
                  <b>{e.title}</b>
                  <span>{e.note}</span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    );
  }

  function Schedule() {
    return (
      <section className="sec">
        <div className="wrap stmt__grid">
          <Reveal><Calendar /></Reveal>
          <div>
            <Reveal as="p" className="eyebrow">창업 일정 관리</Reveal>
            <h2 className="stmt__head">
              <Reveal as="span" className="stmt__line">마감일을 놓치지 않게</Reveal>
              <Reveal as="span" className="stmt__line" delay={120}>
                <em>한 캘린더</em>로 관리합니다
              </Reveal>
            </h2>
            <Reveal as="p" className="stmt__sub" delay={200}>
              지원사업 접수 마감일과 부가세 · 종합소득세 신고일을 한 달력에 모았어요.
              관심 공고를 저장하면 마감 3일 전에 알림을 보내드립니다.
            </Reveal>
            <Reveal as="ul" className="stmt__mini" delay={260}>
              <li><b>D-8</b><span>청년창업사관학교 15기 마감<em>중소벤처기업진흥공단</em></span></li>
              <li><b>D-17</b><span>부가세 2기 예정신고<em>홈택스 전자신고</em></span></li>
              <li><b>D-22</b><span>서울 청년창업 임차보증금 지원 마감<em>서울시</em></span></li>
            </Reveal>
          </div>
        </div>
      </section>
    );
  }

  /* ---------- 홈 3: AI 대화 ---------- */
  function ChatDemo() {
    const [ref, inView] = useInView({ threshold: 0.3 }, true);
    const [shown, setShown] = useState(0);
    const [typing, setTyping] = useState(false);
    const [extra, setExtra] = useState([]);
    const [draft, setDraft] = useState('');
    const bodyRef = useRef(null);

    useEffect(() => {
      if (!inView) {
        setShown(0);
        setTyping(false);
        setExtra([]);
        return;
      }
      if (prefersReducedMotion) {
        setShown(CHAT.length);
        return;
      }
      if (shown >= CHAT.length) return;
      const next = CHAT[shown];
      let t;
      if (next.role === 'ai') {
        setTyping(true);
        t = setTimeout(() => {
          setTyping(false);
          setShown((s) => s + 1);
        }, 950);
      } else {
        t = setTimeout(() => setShown((s) => s + 1), 560);
      }
      return () => clearTimeout(t);
    }, [inView, shown]);

    useEffect(() => {
      if (bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
    }, [shown, typing, extra]);

    const send = (e) => {
      e.preventDefault();
      const q = draft.trim();
      if (!q) return;
      setDraft('');
      setExtra((x) => [...x, { role: 'user', text: q }]);
      setTimeout(() => {
        setExtra((x) => [
          ...x,
          { role: 'ai', text: '실제 서비스에서는 국세청 해석사례와 관련 법령을 인용해 답변하고, 필요한 일정을 캘린더에 등록해 드려요.' },
        ]);
      }, 700);
    };

    const msgs = [...CHAT.slice(0, shown), ...extra];

    return (
      <section className="sec sec--alt">
        <div className="wrap chat__grid">
          <div>
            <Reveal as="p" className="eyebrow">AI 어시스턴트</Reveal>
            <Reveal as="h2" className="chat__title" delay={80}>
              대화하듯 물어보면<br />창업과 세금 업무가 정리됩니다
            </Reveal>
            <Reveal as="p" className="chat__lead" delay={160}>
              지원사업 탐색, 사업자 유형 판단, 세액감면 여부, 신고 일정 등록까지 —
              한 번의 대화로 이어서 처리할 수 있어요.
            </Reveal>
            <Reveal className="chat__tags" delay={220}>
              <span className="chat__tag">지원사업 매칭</span>
              <span className="chat__tag">세액감면 판정</span>
              <span className="chat__tag">신고 일정 등록</span>
              <span className="chat__tag">경비처리 상담</span>
            </Reveal>
          </div>

          <Reveal>
            <div className="chatbox" ref={ref}>
              <div className="chatbox__bar">
                <span className="chatbox__ava" aria-hidden="true">ON</span>
                <span className="chatbox__who">
                  <b>창업ON 어시스턴트</b>
                  <span>온라인 · 보통 몇 초 안에 응답</span>
                </span>
              </div>
              <div className="chatbox__body" ref={bodyRef}>
                {msgs.map((m, i) => (
                  <div key={i} className={`msg msg-in msg--${m.role}`}>{m.text}</div>
                ))}
                {typing && (
                  <div className="typing" aria-label="입력 중">
                    <i /><i /><i />
                  </div>
                )}
              </div>
              <form className="chatbox__input" onSubmit={send}>
                <input
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  placeholder="메시지를 입력해 보세요"
                  aria-label="메시지 입력"
                />
                <button type="submit">전송</button>
              </form>
            </div>
          </Reveal>
        </div>
      </section>
    );
  }

  /* ---------- 홈 4: 창업 A-Z 로드맵 ---------- */
  function rmIcon(k) {
    const p = { fill: 'none', stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round', strokeLinejoin: 'round' };
    const paths = {
      A: <><path d="M9 18h6M10 21h4" {...p} /><path d="M12 3a6 6 0 0 0-4 10.4c.6.5 1 1.4 1 2.6h6c0-1.2.4-2.1 1-2.6A6 6 0 0 0 12 3Z" {...p} /></>,
      B: <><path d="M7 3h8l3 3v15H7z" {...p} /><path d="M15 3v4h4M10 12h5M10 16h5" {...p} /></>,
      C: <><circle cx="12" cy="12" r="8.5" {...p} /><path d="m8.5 12 2.5 2.5 4.5-5" {...p} /></>,
      D: <><circle cx="12" cy="12" r="8.5" {...p} /><path d="M12 7.5v9M9.7 9.7c0-1 1-1.6 2.3-1.6s2.3.6 2.3 1.6-1 1.3-2.3 1.5-2.3.6-2.3 1.6 1 1.6 2.3 1.6 2.3-.6 2.3-1.6" {...p} /></>,
      E: <><path d="m7.5 16.5 9-9" {...p} /><circle cx="8.5" cy="8.5" r="2" {...p} /><circle cx="15.5" cy="15.5" r="2" {...p} /></>,
      F: <><path d="M7 3.5h10v17l-2.5-1.6-2.5 1.6-2.5-1.6L7 20.5z" {...p} /><path d="M10 8h4M10 12h4" {...p} /></>,
      Z: <><path d="m4 15 5-5 3 3 8-8" {...p} /><path d="M16 5h4v4" {...p} /></>,
    };
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        {paths[k] || paths.A}
      </svg>
    );
  }

  function Roadmap() {
    const [ref, inView] = useInView({ threshold: 0.2 }, true);
    const on = inView || prefersReducedMotion;
    return (
      <section className="sec">
        <div className="wrap">
          <Reveal as="p" className="eyebrow">창업 A → Z</Reveal>
          <Reveal as="h2" className="sec__title" delay={80}>
            아이디어부터 스케일업까지
          </Reveal>
          <div className={'rz' + (on ? ' is-in' : '')} ref={ref}>
            <div className="rz__row">
              {ROADMAP.map((s, i) => (
                <React.Fragment key={s.k}>
                  {i > 0 && (
                    <div className="rz__sep" aria-hidden="true" style={{ '--d': `${i * 160 + 80}ms` }}>›</div>
                  )}
                  <div
                    className={'rz__step' + (s.accent ? ' rz__step--accent' : '')}
                    style={{ '--d': `${i * 160 + 150}ms` }}
                  >
                    <span className="rz__ico">{rmIcon(s.k)}</span>
                    <span className="rz__phase">{s.phase}</span>
                    <span className="rz__t">{s.t}</span>
                    <span className="rz__d">{s.d}</span>
                  </div>
                </React.Fragment>
              ))}
            </div>
          </div>
        </div>
      </section>
    );
  }

  function Closing({ onStart }) {
    return (
      <section className="sec">
        <Reveal className="wrap closing">
          <div className="closing__stats">
            {METRICS.map((m, i) => (
              <Metric key={m.label} {...m} delay={i * 70} />
            ))}
          </div>
          <div className="closing__cta">
            <p className="eyebrow">지금 창업ON에서</p>
            <h2>지금, 내 조건으로 시작하세요</h2>
            <p>로그인하면 맞춤 공고와 세무 대시보드가 함께 열립니다.</p>
            <button className="btn btn--primary btn--lg" type="button" onClick={onStart}>
              3분 만에 시작하기
            </button>
          </div>
        </Reveal>
      </section>
    );
  }

  function Home({ onNavigate }) {
    return (
      <main className="home-flow">
        <Hero onNavigate={onNavigate} />
        <Schedule />
        <ChatDemo />
        <Roadmap />
        <Closing onStart={() => onNavigate('mypage')} />
      </main>
    );
  }

  /* ---------- App ---------- */
  function App() {
    const [user, setUser] = useState(null);
    const [view, setView] = useState('home');
    const [pageKey, setPageKey] = useState('tax');
    const [loginOpen, setLoginOpen] = useState(false);
    const [afterLogin, setAfterLogin] = useState(null);

    const goMyPage = () => {
      if (user) setView('mypage');
      else {
        setAfterLogin('mypage');
        setLoginOpen(true);
      }
    };

    const handleNavigate = (key) => {
      if (key === 'home') {
        setView('home');
        window.scrollTo(0, 0);
        return;
      }
      if (key === 'mypage') {
        goMyPage();
        return;
      }
      setPageKey(key); // 'roadmap' | 'tax' | 'gov' | 'ai'
      setView('page');
      window.scrollTo(0, 0);
    };

    const handleLoginClick = () => {
      if (user) {
        setUser(null);
        setView('home');
      } else {
        setAfterLogin(null);
        setLoginOpen(true);
      }
    };

    const handleLoginSuccess = (u) => {
      setUser(u);
      setLoginOpen(false);
      if (afterLogin === 'mypage') setView('mypage');
      setAfterLogin(null);
    };

    const modal = loginOpen && (
      <LoginModal onClose={() => setLoginOpen(false)} onSuccess={handleLoginSuccess} />
    );

    if (view === 'mypage' && user) {
      return (
        <MyPage
          user={user}
          onHome={() => setView('home')}
          onLogout={() => {
            setUser(null);
            setView('home');
          }}
        />
      );
    }

    if (view === 'page') {
      return (
        <React.Fragment>
          <ScrollProgress />
          <SubPage
            pageKey={pageKey}
            user={user}
            onHome={() => setView('home')}
            onLoginClick={handleLoginClick}
            onNavigate={handleNavigate}
          />
          {modal}
        </React.Fragment>
      );
    }

    return (
      <React.Fragment>
        <ScrollProgress />
        <Nav user={user} onLoginClick={handleLoginClick} onNavigate={handleNavigate} />
        <Home onNavigate={handleNavigate} />
        <footer className="foot">
          <div className="wrap">
            창업ON · 공공데이터 기반 창업 지원 공고 큐레이션 &nbsp;·&nbsp; 화면의
            수치와 공고는 데모용 예시 데이터입니다.
          </div>
        </footer>
        {modal}
      </React.Fragment>
    );
  }

export default App;
