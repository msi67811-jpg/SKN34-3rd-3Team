import { useState } from "react";
import { api } from "../api.js";

export default function Tax() {
  const [revenue, setRevenue] = useState(40000000);
  const [diagnosis, setDiagnosis] = useState(null);
  const [reduction, setReduction] = useState(null);
  const [error, setError] = useState("");

  async function runDiagnosis(e) {
    e.preventDefault();
    setDiagnosis(await api.diagnose({ expectedRevenue: Number(revenue), hasEmployee: false }));
  }

  async function runReduction() {
    setError("");
    try {
      setReduction(await api.taxReduction());
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section className="max-w-2xl space-y-6">
      <h2 className="text-2xl font-semibold">세무 · 청년창업 세액감면</h2>

      <form className="card p-5 space-y-3" onSubmit={runDiagnosis}>
        <h3 className="font-semibold">사업자 유형 진단</h3>
        <label className="text-sm">예상 연 매출</label>
        <input className="w-full rounded-xl border border-sand px-3 py-2" type="number" value={revenue} onChange={(e) => setRevenue(e.target.value)} />
        <button className="rounded-xl bg-pine px-4 py-2 text-white">진단하기</button>
        {diagnosis && (
          <div className="text-sm">
            <p className="text-pine font-semibold">추천: {diagnosis.recommendedType}</p>
            <ul className="mt-2 space-y-1">
              {diagnosis.comparison.map((c) => (
                <li key={c.type}>{c.type} — {c.when}</li>
              ))}
            </ul>
          </div>
        )}
      </form>

      <div className="card p-5 space-y-3">
        <h3 className="font-semibold">청년창업 세액감면 Rule 판정</h3>
        <p className="text-sm text-ink/70">온보딩의 나이·창업일·업종으로 판정합니다. LLM 근거 설명은 아직 목업입니다.</p>
        <button className="rounded-xl bg-pine px-4 py-2 text-white" onClick={runReduction}>
          판정 실행
        </button>
        {error && <p className="text-sm text-clay">{error}</p>}
        {reduction && (
          <div>
            <p className={reduction.eligible ? "text-pine font-semibold" : "text-clay font-semibold"}>
              {reduction.eligible ? "요건 충족 가능성이 있습니다" : "요건 미충족으로 보입니다"}
            </p>
            <ul className="mt-2 list-disc pl-5 text-sm">
              {reduction.reasons.map((r) => <li key={r}>{r}</li>)}
            </ul>
            <p className="mt-3 text-xs text-ink/50">{reduction.legalBasis}</p>
          </div>
        )}
      </div>
    </section>
  );
}
