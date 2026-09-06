import { useEffect, useState } from "react";
import { api } from "../api.js";

const field =
  "w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100";

export default function Tax() {
  const [conditions, setConditions] = useState({
    expectedRevenue: 48000000,
    hasEmployee: false,
  });
  const [diagnosis, setDiagnosis] = useState(null);
  const [reduction, setReduction] = useState(null);
  const [taxType, setTaxType] = useState("부가가치세");
  const [details, setDetails] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .taxInfo()
      .then((d) => {
        const info = d.taxInfo || {};
        setTaxType(info.taxType || "부가가치세");
        setDetails(info.details || "");
      })
      .catch(() => {});
    api
      .taxReductionResult()
      .then(setReduction)
      .catch(() => {});
  }, []);

  async function runDiagnosis(e) {
    e.preventDefault();
    setError("");
    try {
      const data = await api.diagnose({
        expectedRevenue: Number(conditions.expectedRevenue),
        hasEmployee: Boolean(conditions.hasEmployee),
      });
      setDiagnosis(data);
    } catch (err) {
      setError(err.message);
    }
  }

  async function runReduction() {
    setError("");
    try {
      const data = await api.taxReduction();
      setReduction(data);
    } catch (err) {
      setError(err.message);
    }
  }

  async function saveTaxInfo(e) {
    e.preventDefault();
    setMessage("");
    setError("");
    try {
      await api.updateTaxInfo({ taxType, details });
      setMessage("세금 메모가 저장되었습니다.");
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section className="space-y-6">
      <header>
        <h2 className="text-2xl font-semibold">세무·감면</h2>
        <p className="text-slate-400">유형 진단은 Rule, 세액감면 설명은 LLM이 가능하면 붙입니다.</p>
      </header>

      <div className="grid gap-6 lg:grid-cols-2">
        <form className="space-y-3 rounded-2xl border border-slate-800 bg-slate-900/60 p-5" onSubmit={runDiagnosis}>
          <h3 className="font-semibold">사업자 유형 진단</h3>
          <input
            className={field}
            type="number"
            value={conditions.expectedRevenue}
            onChange={(e) => setConditions((p) => ({ ...p, expectedRevenue: e.target.value }))}
            placeholder="예상 매출"
          />
          <label className="flex items-center gap-2 text-sm text-slate-300">
            <input
              type="checkbox"
              checked={conditions.hasEmployee}
              onChange={(e) => setConditions((p) => ({ ...p, hasEmployee: e.target.checked }))}
            />
            직원 고용 예정
          </label>
          <button className="w-full rounded-xl bg-cyan-500 py-2.5 font-semibold text-slate-950">진단하기</button>
          {diagnosis && (
            <div className="rounded-xl bg-slate-950/80 p-3 text-sm text-slate-300">
              <p className="text-cyan-200">추천: {diagnosis.recommendedType}</p>
              <ul className="mt-2 list-disc space-y-1 pl-5">
                {(diagnosis.comparison || []).map((row, i) => (
                  <li key={i}>
                    {row.type}: {row.when} — {row.note}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </form>

        <div className="space-y-3 rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
          <h3 className="font-semibold">청년창업 세액감면</h3>
          <p className="text-sm text-slate-400">나이·창업일·업종 정보로 감면 요건을 판정합니다.</p>
          <button
            type="button"
            className="w-full rounded-xl border border-cyan-500/40 bg-cyan-500/10 py-2.5 font-semibold text-cyan-200"
            onClick={runReduction}
          >
            감면 요건 확인
          </button>
          {reduction && (
            <div className="rounded-xl bg-slate-950/80 p-3 text-sm text-slate-300">
              <p className={reduction.eligible ? "text-emerald-300" : "text-amber-300"}>
                {reduction.eligible ? "요건 충족 가능" : "요건 미충족 / 추가 확인 필요"}
              </p>
              <ul className="mt-2 list-disc space-y-1 pl-5">
                {(reduction.reasons || []).map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
              <p className="mt-2 text-xs text-slate-500">{reduction.legalBasis}</p>
              {reduction.llmUsed && <p className="mt-2 text-xs text-emerald-300">LLM 근거 설명 포함</p>}
            </div>
          )}
        </div>
      </div>

      <form className="space-y-3 rounded-2xl border border-slate-800 bg-slate-900/60 p-5" onSubmit={saveTaxInfo}>
        <h3 className="font-semibold">세금 메모</h3>
        <input className={field} value={taxType} onChange={(e) => setTaxType(e.target.value)} placeholder="세목" />
        <textarea
          className={`${field} min-h-24`}
          value={details}
          onChange={(e) => setDetails(e.target.value)}
          placeholder="신고 메모"
        />
        <button className="rounded-xl bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-900">저장</button>
        {message && <p className="text-sm text-emerald-300">{message}</p>}
      </form>

      {error && <p className="text-sm text-rose-300">{error}</p>}
    </section>
  );
}
