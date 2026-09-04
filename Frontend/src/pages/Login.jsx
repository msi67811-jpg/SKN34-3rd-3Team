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
      navigate("/");
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="min-h-screen grid place-items-center px-4">
      <div className="card w-full max-w-md p-8">
        <p className="text-xs tracking-[0.2em] text-moss">DB·LLM 없이 동작하는 목업</p>
        <h1 className="mt-2 text-2xl font-semibold">청년창업 지원 플랫폼</h1>
        <p className="mt-2 text-sm text-ink/70">
          데모 계정: demo@demo.com / demo123
        </p>
        <form className="mt-6 space-y-3" onSubmit={submit}>
          {mode === "signup" && (
            <input
              className="w-full rounded-xl border border-sand px-3 py-2"
              placeholder="이름"
              value={form.name}
              onChange={(e) => set("name", e.target.value)}
            />
          )}
          <input
            className="w-full rounded-xl border border-sand px-3 py-2"
            placeholder="이메일"
            value={form.email}
            onChange={(e) => set("email", e.target.value)}
          />
          <input
            type="password"
            className="w-full rounded-xl border border-sand px-3 py-2"
            placeholder="비밀번호"
            value={form.password}
            onChange={(e) => set("password", e.target.value)}
          />
          {error && <p className="text-sm text-clay">{error}</p>}
          <button className="w-full rounded-xl bg-pine py-2.5 text-white">
            {mode === "login" ? "로그인" : "회원가입 후 로그인"}
          </button>
        </form>
        <button
          className="mt-4 text-sm underline text-moss"
          onClick={() => setMode(mode === "login" ? "signup" : "login")}
        >
          {mode === "login" ? "계정이 없으면 회원가입" : "이미 계정이 있으면 로그인"}
        </button>
      </div>
    </div>
  );
}
