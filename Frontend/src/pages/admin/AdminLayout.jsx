import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { api } from "../../api.js";

const links = [
  ["/admin", "대시보드"],
  ["/admin/users", "사용자 관리"],
  ["/admin/documents", "세법·정책·공고"],
];

export default function AdminLayout() {
  const navigate = useNavigate();

  function logout() {
    api.logout().catch(() => {});
    localStorage.removeItem("accessToken");
    localStorage.removeItem("userName");
    localStorage.removeItem("userRole");
    navigate("/admin/login");
  }

  return (
    <div className="min-h-screen md:grid md:grid-cols-[240px_1fr]">
      <aside className="bg-[#3b2a14] px-5 py-8 text-[#f6f1e8]">
        <p className="text-xs uppercase tracking-[0.2em] text-[#e8b86d]">Admin</p>
        <h1 className="mt-2 text-xl font-semibold">관리자 콘솔</h1>
        <nav className="mt-8 space-y-1">
          {links.map(([to, label]) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/admin"}
              className={({ isActive }) =>
                `block rounded-xl px-3 py-2 text-sm ${isActive ? "bg-[#e8b86d] text-[#3b2a14]" : "hover:bg-white/10"}`
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
        <button className="mt-10 text-sm text-[#e8b86d] underline" onClick={logout}>
          로그아웃
        </button>
      </aside>
      <main className="px-5 py-8 md:px-10">
        <Outlet />
      </main>
    </div>
  );
}
