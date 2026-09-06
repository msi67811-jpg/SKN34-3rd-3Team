import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";

export default function Login() {
  const navigate = useNavigate();
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({
    email: "demo@demo.com",
    password: "demo123",
    name: "김창업",
  });
  const [error, setError] = useState("");

  function set(key, value) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function submit(e) {
    e.preventDefault();
    setError("");
    try {
      if (mode === "signup") {
        await api.signup(form);
      }
      const data = await api.login({ email: form.email, password: form.password });
      localStorage.setItem("accessToken", data.accessToken);
      localStorage.setItem("userName", data.name);
      localStorage.setItem("userRole", data.role || "user");
      navigate(data.role === "admin" ? "/admin" : "/");
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="grid min-h-screen place-items-center px-4">
      <div className="grid w-full max-w-5xl overflow-hidden rounded-[2rem] border border-[#e4dccb] bg-white shadow-[0_24px_80px_rgba(16,35,28,0.08)] md:grid-cols-2">
        <div className="bg-[#10231c] px-8 py-12 text-[#f6f1e8]">
          <p className="text-xs uppercase tracking-[0.22em] text-[#e8b86d]">Youth Founder Desk</p>
          <h1 className="mt-4 text-3xl font-semibold leading-snug">
            세금·지원정책·지출을
            <br />
            한 화면에서
          </h1>
          <p className="mt-4 text-sm leading-6 text-[#c9d7d0]">
            데모 계정으로 캘린더, RAG 상담, 영수증, 관리자 콘솔까지 바로 확인할 수 있습니다.
          </p>
        </div>
        <div className="px-8 py-12">
          <h2 className="text-2xl font-semibold text-[#10231c]">
            {mode === "login" ? "로그인" : "회원가입"}
          </h2>
          <p className="mt-2 text-sm text-neutral-500">demo@demo.com / demo123</p>
          <form className="mt-6 space-y-3" onSubmit={submit}>
            {mode === "signup" && (
              <input className="ui-field" placeholder="이름" value={form.name} onChange={(e) => set("name", e.target.value)} />
            )}
            <input className="ui-field" placeholder="이메일" value={form.email} onChange={(e) => set("email", e.target.value)} />
            <input
              type="password"
              className="ui-field"
              placeholder="비밀번호"
              value={form.password}
              onChange={(e) => set("password", e.target.value)}
            />
            {error && <p className="text-sm text-rose-600">{error}</p>}
            <button className="ui-btn w-full">{mode === "login" ? "로그인" : "회원가입 후 로그인"}</button>
          </form>
          <button className="mt-4 text-sm text-[#1f6b4f] underline" onClick={() => setMode(mode === "login" ? "signup" : "login")}>
            {mode === "login" ? "계정이 없으면 회원가입" : "이미 계정이 있으면 로그인"}
          </button>
          <p className="mt-4">
            <a className="text-sm text-[#a16207] underline" href="/admin/login">
              관리자 로그인
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
