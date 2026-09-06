import { useEffect, useState } from "react";
import { api } from "../../api.js";

const field = "w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm";

export default function AdminDocuments() {
  const [tab, setTab] = useState("tax");
  const [docs, setDocs] = useState([]);
  const [policies, setPolicies] = useState([]);
  const [announcements, setAnnouncements] = useState([]);
  const [error, setError] = useState("");
  const [taxForm, setTaxForm] = useState({ title: "", lawName: "", content: "", source: "국세청" });
  const [policyForm, setPolicyForm] = useState({
    title: "",
    region: "전국",
    industry: "전 업종",
    target: "",
    benefit: "",
    eligibilityRule: "age<=39",
    source: "",
    applyStartDate: "2026-09-01",
    applyEndDate: "2026-09-30",
    applyMethod: "온라인 신청",
    content: "",
  });

  async function load() {
    const [tax, policy, announcement] = await Promise.all([
      api.adminTaxDocuments(),
      api.adminPolicies(),
      api.adminAnnouncements(),
    ]);
    setDocs(tax.documents || []);
    setPolicies(policy.policies || []);
    setAnnouncements(announcement.announcements || []);
  }

  useEffect(() => {
    load().catch((e) => setError(e.message));
  }, []);

  async function createTax(e) {
    e.preventDefault();
    await api.adminCreateTaxDocument(taxForm);
    setTaxForm({ title: "", lawName: "", content: "", source: "국세청" });
    await load();
  }

  async function createPolicy(e) {
    e.preventDefault();
    await api.adminCreatePolicy(policyForm);
    await load();
  }

  return (
    <section className="space-y-6">
      <header>
        <h2 className="text-2xl font-semibold">세법·정책·공고 관리</h2>
        <p className="text-slate-400">등록한 정책은 사용자 화면 검색·캘린더에 바로 반영됩니다.</p>
      </header>

      <div className="flex gap-2">
        {[
          ["tax", "세법 자료"],
          ["policy", "정책"],
          ["announcement", "공고"],
        ].map(([id, label]) => (
          <button
            key={id}
            className={`rounded-xl px-3 py-2 text-sm ${
              tab === id ? "bg-amber-500/20 text-amber-100" : "bg-slate-900 text-slate-300"
            }`}
            onClick={() => setTab(id)}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "tax" && (
        <div className="grid gap-6 lg:grid-cols-2">
          <form className="space-y-3 rounded-2xl border border-slate-800 bg-slate-900/60 p-5" onSubmit={createTax}>
            <h3 className="font-semibold">세법 자료 등록</h3>
            <input className={field} placeholder="제목" value={taxForm.title} onChange={(e) => setTaxForm({ ...taxForm, title: e.target.value })} />
            <input className={field} placeholder="법령명" value={taxForm.lawName} onChange={(e) => setTaxForm({ ...taxForm, lawName: e.target.value })} />
            <textarea className={field} rows={4} placeholder="내용" value={taxForm.content} onChange={(e) => setTaxForm({ ...taxForm, content: e.target.value })} />
            <input className={field} placeholder="출처" value={taxForm.source} onChange={(e) => setTaxForm({ ...taxForm, source: e.target.value })} />
            <button className="rounded-xl bg-amber-400 px-4 py-2 font-semibold text-slate-950">등록</button>
          </form>
          <ul className="space-y-2">
            {docs.map((doc) => (
              <li key={doc.id} className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 text-sm">
                <p className="font-medium">{doc.title}</p>
                <p className="mt-1 text-slate-500">{doc.source}</p>
              </li>
            ))}
          </ul>
        </div>
      )}

      {tab === "policy" && (
        <div className="grid gap-6 lg:grid-cols-2">
          <form className="space-y-3 rounded-2xl border border-slate-800 bg-slate-900/60 p-5" onSubmit={createPolicy}>
            <h3 className="font-semibold">정책 등록</h3>
            <input className={field} placeholder="정책명" value={policyForm.title} onChange={(e) => setPolicyForm({ ...policyForm, title: e.target.value })} required />
            <input className={field} placeholder="지역" value={policyForm.region} onChange={(e) => setPolicyForm({ ...policyForm, region: e.target.value })} />
            <input className={field} placeholder="업종" value={policyForm.industry} onChange={(e) => setPolicyForm({ ...policyForm, industry: e.target.value })} />
            <input className={field} placeholder="대상" value={policyForm.target} onChange={(e) => setPolicyForm({ ...policyForm, target: e.target.value })} />
            <textarea className={field} rows={3} placeholder="지원 내용" value={policyForm.benefit} onChange={(e) => setPolicyForm({ ...policyForm, benefit: e.target.value })} />
            <input className={field} placeholder="자격 규칙 예: age<=39,region=서울" value={policyForm.eligibilityRule} onChange={(e) => setPolicyForm({ ...policyForm, eligibilityRule: e.target.value })} />
            <input className={field} placeholder="출처" value={policyForm.source} onChange={(e) => setPolicyForm({ ...policyForm, source: e.target.value })} />
            <div className="grid grid-cols-2 gap-2">
              <input className={field} type="date" value={policyForm.applyStartDate} onChange={(e) => setPolicyForm({ ...policyForm, applyStartDate: e.target.value })} />
              <input className={field} type="date" value={policyForm.applyEndDate} onChange={(e) => setPolicyForm({ ...policyForm, applyEndDate: e.target.value })} />
            </div>
            <input className={field} placeholder="신청 방법" value={policyForm.applyMethod} onChange={(e) => setPolicyForm({ ...policyForm, applyMethod: e.target.value })} />
            <textarea className={field} rows={3} placeholder="공고 원문(선택)" value={policyForm.content} onChange={(e) => setPolicyForm({ ...policyForm, content: e.target.value })} />
            <button className="rounded-xl bg-amber-400 px-4 py-2 font-semibold text-slate-950">등록</button>
          </form>
          <ul className="space-y-2">
            {policies.map((policy) => (
              <li key={policy.id} className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 text-sm">
                <p className="font-medium">{policy.title}</p>
                <p className="mt-1 text-slate-500">
                  {policy.region} · {policy.industry}
                </p>
              </li>
            ))}
          </ul>
        </div>
      )}

      {tab === "announcement" && (
        <ul className="space-y-2">
          {announcements.map((item) => (
            <li key={item.id} className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 text-sm">
              <p className="font-medium">공고 #{item.id} · 정책 {item.policy_id}</p>
              <p className="mt-1 text-slate-400">{item.raw_content}</p>
              <p className="mt-1 text-xs text-slate-500">
                {String(item.apply_start_date || "").slice(0, 10)} ~ {String(item.apply_end_date || "").slice(0, 10)}
              </p>
            </li>
          ))}
          {!announcements.length && <li className="text-slate-500">등록된 공고가 없습니다.</li>}
        </ul>
      )}
      {error && <p className="text-sm text-rose-300">{error}</p>}
    </section>
  );
}
