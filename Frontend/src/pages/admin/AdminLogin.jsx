import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../../api.js";

export default function AdminLogin() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "admin@demo.com", password: "admin123" });
  const [error, setError] = useState("");

  async function submit(e) {
    e.preventDefault();
    setError("");
    try {
      const data = await api.adminLogin(form);
      localStorage.setItem("accessToken", data.accessToken);
      localStorage.setItem("userName", data.name || "관리자");
      localStorage.setItem("userRole", "admin");
      navigate("/admin");
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="grid min-h-screen place-items-center px-4">
      <div className="ui-card w-full max-w-md p-8">
        <p className="text-xs uppercase tracking-[0.2em] text-[#a16207]">Admin</p>
        <h1 className="mt-2 text-2xl font-semibold">관리자 로그인</h1>
        <p className="mt-2 text-sm text-neutral-500">admin@demo.com / admin123</p>
        <form className="mt-6 space-y-3" onSubmit={submit}>
          <input className="ui-field" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          <input
            type="password"
            className="ui-field"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
          />
          {error && <p className="text-sm text-rose-600">{error}</p>}
          <button className="w-full rounded-xl bg-[#3b2a14] py-2.5 font-semibold text-white">관리자 로그인</button>
        </form>
        <Link className="mt-4 inline-block text-sm text-[#1f6b4f] underline" to="/login">
          일반 사용자 로그인
        </Link>
      </div>
    </div>
  );
}
