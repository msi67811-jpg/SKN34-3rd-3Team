import { NavLink, Outlet, useNavigate } from "react-router-dom";

const links = [
  ["/", "홈·캘린더"],
  ["/chat", "AI 상담"],
  ["/policies", "지원정책"],
  ["/tax", "세무·감면"],
  ["/expenses", "지출"],
  ["/onboarding", "온보딩"],
  ["/profile", "프로필"],
];

export default function Layout() {
  const navigate = useNavigate();
  const name = localStorage.getItem("userName") || "회원";

  function logout() {
    localStorage.removeItem("accessToken");
    localStorage.removeItem("userName");
    navigate("/login");
  }

  return (
    <div className="min-h-screen grid grid-cols-1 md:grid-cols-[240px_1fr]">
      <aside className="bg-ink text-paper px-5 py-8">
        <p className="text-xs tracking-[0.2em] text-sand/70">SKN34 · 3TEAM</p>
        <h1 className="mt-2 text-xl font-semibold leading-snug">
          청년·1인 창업
          <br />
          행정 지원
        </h1>
        <nav className="mt-8 space-y-1">
          {links.map(([to, label]) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `block rounded-xl px-3 py-2 text-sm ${
                  isActive ? "bg-pine text-white" : "text-sand/80 hover:bg-white/5"
                }`
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-10 text-sm text-sand/70">
          <p>{name}님</p>
          <button className="mt-2 underline" onClick={logout}>
            로그아웃
          </button>
        </div>
      </aside>
      <main className="px-5 py-8 md:px-10">
        <Outlet />
      </main>
    </div>
  );
}
