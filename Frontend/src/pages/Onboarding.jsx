import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";

const field =
  "w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100";

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
    setMessage("저장되었습니다.");
    setTimeout(() => navigate("/"), 500);
  }

  return (
    <section className="max-w-2xl">
      <h2 className="text-2xl font-semibold">내 사업 정보</h2>
      <p className="mt-2 text-slate-400">나이·지역·업종을 넣으면 세금 감면과 지원 정책 추천에 반영됩니다.</p>
      <form className="mt-6 grid gap-3 rounded-2xl border border-slate-800 bg-slate-900/60 p-6" onSubmit={submit}>
        <input className={field} value={form.name} onChange={(e) => set("name", e.target.value)} placeholder="이름" />
        <input className={field} type="number" value={form.age} onChange={(e) => set("age", e.target.value)} placeholder="나이" />
        <input className={field} value={form.region} onChange={(e) => set("region", e.target.value)} placeholder="거주 지역" />
        <select className={field} value={form.businessType} onChange={(e) => set("businessType", e.target.value)}>
          <option>예비창업</option>
          <option>간이과세자</option>
          <option>일반과세자</option>
        </select>
        <input className={field} value={form.industry} onChange={(e) => set("industry", e.target.value)} placeholder="업종" />
        <label className="text-sm text-slate-400">창업일</label>
        <input className={field} type="date" value={form.foundedAt} onChange={(e) => set("foundedAt", e.target.value)} />
        <label className="text-sm text-slate-400">사업자등록일</label>
        <input className={field} type="date" value={form.businessRegisteredAt} onChange={(e) => set("businessRegisteredAt", e.target.value)} />
        <button className="rounded-xl bg-cyan-500 py-2.5 font-semibold text-slate-950">저장하고 홈으로</button>
        {message && <p className="text-sm text-emerald-300">{message}</p>}
      </form>
    </section>
  );
}
