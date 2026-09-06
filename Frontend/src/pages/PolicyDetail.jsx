import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../api.js";

export default function PolicyDetail() {
  const { id } = useParams();
  const [detail, setDetail] = useState(null);
  const [eligibility, setEligibility] = useState(null);
  const [summary, setSummary] = useState(null);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");
  const [loadingSummary, setLoadingSummary] = useState(false);

  useEffect(() => {
    api
      .policy(id)
      .then(setDetail)
      .catch((e) => setError(e.message));
  }, [id]);

  async function checkEligibility() {
    const data = await api.eligibility(id);
    setEligibility(data);
  }

  async function save() {
    await api.savePolicy(id);
    setSaved(true);
  }

  async function loadSummary() {
    if (!detail?.announcementId) return;
    setLoadingSummary(true);
    setError("");
    try {
      const data = await api.announcementSummary(detail.announcementId);
      setSummary(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingSummary(false);
    }
  }

  if (error && !detail) {
    return <p className="text-rose-300">{error}</p>;
  }
  if (!detail) {
    return <p className="text-slate-400">불러오는 중...</p>;
  }

  const policy = detail.policy || detail;

  return (
    <section className="max-w-3xl space-y-4">
      <Link to="/policies" className="text-sm text-cyan-300 underline">
        ← 목록으로
      </Link>
      <h2 className="text-2xl font-semibold">{policy.title}</h2>
      <p className="text-slate-300">{policy.benefit}</p>
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 text-sm text-slate-300">
        <p>
          <span className="text-slate-500">지역</span> {policy.region}
        </p>
        <p className="mt-2">
          <span className="text-slate-500">업종</span> {policy.industry}
        </p>
        <p className="mt-2">
          <span className="text-slate-500">대상</span> {policy.target}
        </p>
        <p className="mt-2">
          <span className="text-slate-500">출처</span> {policy.source}
        </p>
        <p className="mt-2">
          <span className="text-slate-500">신청 기간</span> {detail.applyPeriod}
        </p>
        <p className="mt-2">
          <span className="text-slate-500">신청 방법</span> {detail.applyMethod}
        </p>
        <p className="mt-2">
          <span className="text-slate-500">마감</span> {String(policy.applyEndDate || "").slice(0, 10) || "-"}
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        <button className="rounded-xl bg-cyan-500 px-4 py-2 font-semibold text-slate-950" onClick={checkEligibility}>
          자격 확인
        </button>
        <button className="rounded-xl border border-slate-600 px-4 py-2 text-slate-200" onClick={save}>
          {saved ? "저장됨" : "관심 정책 저장"}
        </button>
        <button
          className="rounded-xl border border-cyan-500/40 px-4 py-2 text-cyan-200 disabled:opacity-50"
          onClick={loadSummary}
          disabled={!detail.announcementId || loadingSummary}
        >
          {loadingSummary ? "요약 중..." : "공고 AI 요약"}
        </button>
      </div>

      {eligibility && (
        <div className="rounded-2xl border border-slate-800 bg-slate-950/80 p-5 text-sm text-slate-300">
          <p className={eligibility.eligible ? "text-emerald-300" : "text-amber-300"}>
            {eligibility.eligible ? "지원 가능으로 보입니다" : "추가 확인이 필요합니다"}
          </p>
          <ul className="mt-2 list-disc space-y-1 pl-5">
            {(eligibility.reasons || []).map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </div>
      )}

      {summary && (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 text-sm text-slate-300">
          <h3 className="font-semibold text-slate-100">공고 요약 {summary.llmUsed ? "(LLM)" : "(규칙)"}</h3>
          <p className="mt-2">대상: {summary.target}</p>
          <p className="mt-2">내용: {summary.benefit}</p>
          <p className="mt-2">기간: {summary.period}</p>
          <p className="mt-2">서류: {summary.documents}</p>
          <p className="mt-2 text-slate-400">{summary.notes}</p>
        </div>
      )}
      {error && detail && <p className="text-sm text-rose-300">{error}</p>}
    </section>
  );
}
