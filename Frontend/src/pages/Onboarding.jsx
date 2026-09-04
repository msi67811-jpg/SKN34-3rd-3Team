import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";

export default function Onboarding() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    name: "",
    age: 29,
    region: "서울",
    businessType: "간이과세자",
    industry: "소프트웨어",
    foundedAt: "2024-03-01",
    businessRegisteredAt: "2024-03-01",
  });
  const [message, setMessage] = useState("");

  useEffect(() => {
    Promise.all([api.me(), api.business()]).then(([me, biz]) => {
      setForm((prev) => ({
        ...prev,
        name: me.name || prev.name,
        age: me.age || prev.age,
        region: me.region || prev.region,
        businessType: biz.businessType || prev.businessType,
        industry: biz.industry || prev.industry,
        foundedAt: biz.foundedAt || prev.foundedAt,
        businessRegisteredAt: biz.businessRegisteredAt || prev.businessRegisteredAt,
      }));
    });
  }, []);

  function set(key, value) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function submit(e) {
    e.preventDefault();
    await api.updateMe({ name: form.name, age: Number(form.age), region: form.region });
    await api.updateBusiness({
      businessType: form.businessType,
      industry: form.industry,
      foundedAt: form.foundedAt,
      businessRegisteredAt: form.businessRegisteredAt,
    });
    localStorage.setItem("userName", form.name);
    setMessage("온보딩 정보가 저장되었습니다.");
    setTimeout(() => navigate("/"), 600);
  }

  return (
    <section className="max-w-2xl">
      <h2 className="text-2xl font-semibold">맞춤 온보딩</h2>
      <p className="mt-2 text-ink/70">
        이 정보는 세액감면 판정, 정책 추천, 챗봇 컨텍스트에 쓰입니다.
      </p>
      <form className="card mt-6 grid gap-3 p-6" onSubmit={submit}>
        <input className="rounded-xl border border-sand px-3 py-2" value={form.name} onChange={(e) => set("name", e.target.value)} placeholder="이름" />
        <input className="rounded-xl border border-sand px-3 py-2" type="number" value={form.age} onChange={(e) => set("age", e.target.value)} placeholder="나이" />
        <input className="rounded-xl border border-sand px-3 py-2" value={form.region} onChange={(e) => set("region", e.target.value)} placeholder="거주 지역" />
        <select className="rounded-xl border border-sand px-3 py-2" value={form.businessType} onChange={(e) => set("businessType", e.target.value)}>
          <option>예비창업</option>
          <option>간이과세자</option>
          <option>일반과세자</option>
        </select>
        <input className="rounded-xl border border-sand px-3 py-2" value={form.industry} onChange={(e) => set("industry", e.target.value)} placeholder="업종" />
        <label className="text-sm text-ink/60">창업일</label>
        <input className="rounded-xl border border-sand px-3 py-2" type="date" value={form.foundedAt} onChange={(e) => set("foundedAt", e.target.value)} />
        <label className="text-sm text-ink/60">사업자등록일</label>
        <input className="rounded-xl border border-sand px-3 py-2" type="date" value={form.businessRegisteredAt} onChange={(e) => set("businessRegisteredAt", e.target.value)} />
        <button className="rounded-xl bg-pine py-2.5 text-white">저장하고 홈으로</button>
        {message && <p className="text-sm text-moss">{message}</p>}
      </form>
    </section>
  );
}
