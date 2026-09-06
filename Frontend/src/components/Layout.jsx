import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { api } from "../api.js";

const links = [
  ["/", "홈·캘린더"],
  ["/chat", "AI 상담"],
  ["/policies", "지원정책"],
  ["/tax", "세무·감면"],
  ["/expenses", "지출"],
  ["/onboarding", "내 사업 정보"],
  ["/profile", "프로필"],
];

export default function Layout() {
  const navigate = useNavigate();
  const name = localStorage.getItem("userName") || "회원";
  const [inbox, setInbox] = useState({ notifications: [], unread: 0 });
  const [open, setOpen] = useState(false);

  async function loadInbox() {
    const data = await api.notifications();
    setInbox({ notifications: data.notifications || [], unread: data.unread || 0 });
    if (typeof Notification !== "undefined" && Notification.permission === "granted") {
      (data.notifications || [])
        .filter((item) => !item.read && item.channel === "push")
        .slice(0, 1)
        .forEach((item) => new Notification(item.title, { body: item.body }));
    }
  }

  useEffect(() => {
    loadInbox().catch(() => {});
    const timer = setInterval(() => loadInbox().catch(() => {}), 5000);
    return () => clearInterval(timer);
  }, []);

  function logout() {
    localStorage.removeItem("accessToken");
    localStorage.removeItem("userName");
    localStorage.removeItem("userRole");
    navigate("/login");
  }

  async function enablePush() {
    if (typeof Notification === "undefined") return;
    await Notification.requestPermission();
  }

  return (
    <div className="min-h-screen text-[#10231c] md:grid md:grid-cols-[260px_1fr]">
      <aside className="border-b border-[#e4dccb] bg-[#10231c] px-5 py-8 text-[#f6f1e8] md:border-b-0 md:border-r md:border-[#1f3b31]">
        <p className="text-[11px] uppercase tracking-[0.2em] text-[#e8b86d]">SKN 34 · 3Team</p>
        <h1 className="mt-3 text-2xl font-semibold leading-snug">
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
                `block rounded-xl px-3 py-2 text-sm transition ${
                  isActive ? "bg-[#1f6b4f] text-white" : "text-[#d9efe6] hover:bg-white/10"
                }`
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-10 text-sm text-[#c9d7d0]">
          <p className="font-medium text-white">{name}님</p>
          <button className="mt-3 text-[#e8b86d] underline" onClick={logout}>
            로그아웃
          </button>
        </div>
      </aside>
      <main className="relative px-5 py-8 md:px-10">
        <div className="mb-6 flex justify-end gap-2">
          <button className="rounded-full border border-[#d8d0c0] bg-white px-3 py-1.5 text-xs" onClick={enablePush}>
            브라우저 알림 허용
          </button>
          <button
            className="relative rounded-full border border-[#d8d0c0] bg-white px-3 py-1.5 text-xs"
            onClick={() => setOpen((value) => !value)}
          >
            알림함 {inbox.unread ? `(${inbox.unread})` : ""}
          </button>
        </div>
        {open && (
          <div className="ui-card absolute right-5 top-16 z-10 w-80 p-4 md:right-10">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold">메일·푸시 알림</h3>
              <button className="text-xs text-[#1f6b4f] underline" onClick={() => api.readAllNotifications().then(loadInbox)}>
                모두 읽음
              </button>
            </div>
            <ul className="mt-3 max-h-72 space-y-2 overflow-y-auto text-sm">
              {inbox.notifications.map((item) => (
                <li key={item.id} className={item.read ? "text-neutral-500" : "text-[#10231c]"}>
                  <p className="font-medium">{item.title}</p>
                  <p className="text-xs">{item.body}</p>
                  <p className="mt-1 text-[11px] text-neutral-400">
                    {item.channel} · {item.status}
                  </p>
                </li>
              ))}
              {!inbox.notifications.length && <li className="text-neutral-500">도착한 알림이 없습니다.</li>}
            </ul>
          </div>
        )}
        <Outlet />
      </main>
    </div>
  );
}
