import { useEffect, useState } from "react";
import { api } from "../../api.js";

export default function AdminDashboard() {
  const [metrics, setMetrics] = useState(null);
  const [reindex, setReindex] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function load() {
    const data = await api.adminMonitoring();
    setMetrics(data.metrics || {});
  }

  useEffect(() => {
    load().catch((e) => setError(e.message));
  }, []);

  async function runReindex() {
    setLoading(true);
    setError("");
    try {
      const data = await api.adminReindex();
      setReindex(data);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  const cards = [
    ["전체 회원", metrics?.users],
    ["활성 회원", metrics?.activeUsers],
    ["정지 회원", metrics?.suspendedUsers],
    ["정책", metrics?.policies],
    ["공고", metrics?.announcements],
    ["세법 자료", metrics?.taxDocuments],
    ["상담 메시지", metrics?.chatMessages],
    ["지출", metrics?.expenses],
    ["리마인더", metrics?.reminders],
  ];

  return (
    <section className="space-y-6">
      <header>
        <h2 className="text-2xl font-semibold">시스템 모니터링</h2>
        <p className="text-slate-400">회원·데이터 현황과 RAG 재색인을 여기서 확인합니다.</p>
      </header>

      <p className="text-sm text-neutral-500">
        Postgres {metrics?.postgres?.reachable ? "연결" : "대기"} · pgvector{" "}
        {metrics?.postgres?.pgvector ? "준비" : "없음"} · RAG chunks {metrics?.postgres?.ragChunks ?? 0}
      </p>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {cards.map(([label, value]) => (
          <div key={label} className="ui-card p-4">
            <p className="text-xs text-slate-500">{label}</p>
            <p className="mt-2 text-2xl font-semibold">{value ?? "-"}</p>
          </div>
        ))}
      </div>

      <div className="ui-card p-5">
        <h3 className="font-semibold">LLM / RAG</h3>
        <p className="mt-2 text-sm text-slate-300">
          LLM {metrics?.llm?.reachable ? "연결" : "대기"} · 인덱스 {metrics?.ragReady ? "준비됨" : "없음"}
        </p>
        <button
          className="mt-4 rounded-xl bg-amber-400 px-4 py-2 font-semibold text-slate-950 disabled:opacity-50"
          onClick={runReindex}
          disabled={loading}
        >
          {loading ? "재색인 중..." : "RAG 문서 재색인"}
        </button>
        {reindex && (
          <p className="mt-3 text-sm text-slate-400">
            결과: {reindex.status} {reindex.llm?.ragReady ? "· 인덱스 준비" : ""}
          </p>
        )}
      </div>
      {error && <p className="text-sm text-rose-300">{error}</p>}
    </section>
  );
}
