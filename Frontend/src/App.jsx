import { useCallback, useEffect, useState } from "react";

const API_URL = (import.meta.env.VITE_LLM_API_URL ?? "http://localhost:8000")
  .replace(/\/$/, "");

const LABELS = {
  llm: "LLM 모델",
  embedding: "Embedding 모델",
  data_source: "Vector Store",
};

async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, options);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body.detail ?? `HTTP ${response.status}`);
  }
  return body;
}

function StatusBadge({ state }) {
  if (state === "in_memory") {
    return (
      <span className="rounded-full bg-cyan-100 px-3 py-1 text-xs font-semibold text-cyan-700">
        In-memory
      </span>
    );
  }

  const configured = state === "configured";
  return (
    <span
      className={`rounded-full px-3 py-1 text-xs font-semibold ${
        configured
          ? "bg-emerald-100 text-emerald-700"
          : "bg-amber-100 text-amber-700"
      }`}
    >
      {configured ? "설정 완료" : "설정 필요"}
    </span>
  );
}

function App() {
  const [health, setHealth] = useState(null);
  const [ready, setReady] = useState(null);
  const [question, setQuestion] = useState("");
  const [userId, setUserId] = useState("1");
  const [topK, setTopK] = useState("3");
  const [answer, setAnswer] = useState(null);
  const [loading, setLoading] = useState(false);
  const [indexing, setIndexing] = useState(false);
  const [answering, setAnswering] = useState(false);
  const [error, setError] = useState("");

  const checkStatus = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [healthResult, readyResult] = await Promise.all([
        apiRequest("/health"),
        apiRequest("/internal/rag/ready"),
      ]);
      setHealth(healthResult);
      setReady(readyResult);
    } catch (requestError) {
      setHealth(null);
      setReady(null);
      setError(`LLM 서비스에 연결하지 못했습니다. (${requestError.message})`);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    checkStatus();
  }, [checkStatus]);

  async function createIndex() {
    setIndexing(true);
    setError("");
    try {
      await apiRequest("/internal/rag/index", { method: "POST" });
      await checkStatus();
    } catch (requestError) {
      setError(`인덱스를 생성하지 못했습니다. (${requestError.message})`);
    } finally {
      setIndexing(false);
    }
  }

  async function submitQuestion(event) {
    event.preventDefault();
    setAnswering(true);
    setError("");
    setAnswer(null);
    try {
      const payload = {
        user_id: Number(userId),
        question,
        top_k: Number(topK),
      };
      setAnswer(
        await apiRequest("/internal/rag/recommendations", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        }),
      );
    } catch (requestError) {
      setError(`답변을 생성하지 못했습니다. (${requestError.message})`);
    } finally {
      setAnswering(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-950 px-5 py-10 text-slate-100">
      <div className="mx-auto max-w-6xl">
        <header className="mb-8 flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="mb-2 text-sm font-semibold tracking-[0.18em] text-cyan-400 uppercase">
              Development tool
            </p>
            <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
              LLM RAG Test Console
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-400">
              Mock 사용자 조건과 질문으로 전체 정책을 검색하고 관련 문서를
              요약하는 임시 개발 화면입니다.
            </p>
          </div>
          <button
            type="button"
            onClick={checkStatus}
            disabled={loading}
            className="rounded-xl bg-cyan-400 px-5 py-3 text-sm font-bold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-wait disabled:opacity-60"
          >
            {loading ? "확인 중..." : "상태 새로고침"}
          </button>
        </header>

        {error ? (
          <div className="mb-5 rounded-xl border border-rose-900 bg-rose-950/40 p-4 text-sm text-rose-200">
            {error}
          </div>
        ) : null}

        <section className="grid gap-5 lg:grid-cols-[0.8fr_1.2fr]">
          <div className="space-y-5">
            <article className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6">
              <div className="mb-5 flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-400">LLM API</p>
                  <p className="mt-1 font-mono text-xs text-cyan-300">{API_URL}</p>
                </div>
                <span
                  className={`h-3 w-3 rounded-full ${
                    health ? "bg-emerald-400" : "bg-rose-400"
                  }`}
                />
              </div>
              {health ? (
                <ul className="space-y-3">
                  {Object.entries(health.components).map(([name, state]) => (
                    <li
                      key={name}
                      className="flex items-center justify-between rounded-xl border border-slate-800 px-4 py-3"
                    >
                      <span className="text-sm font-medium">{LABELS[name]}</span>
                      <StatusBadge state={state} />
                    </li>
                  ))}
                </ul>
              ) : null}
            </article>

            <article className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6">
              <p className="text-sm font-semibold text-cyan-300">RAG index</p>
              <div className="mt-3 flex items-center justify-between">
                <div>
                  <p className="text-lg font-bold">
                    {ready?.index_ready ? "검색 준비 완료" : "인덱스 생성 필요"}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    문서 {ready?.document_count ?? 0}개 · Chunk {ready?.chunk_count ?? 0}개
                    {ready?.index_source
                      ? ` · ${ready.index_source === "cache" ? "로컬 캐시" : "새 임베딩"}`
                      : ""}
                  </p>
                </div>
                <span
                  className={`rounded-full px-3 py-1 text-xs font-bold ${
                    ready?.index_ready
                      ? "bg-emerald-100 text-emerald-700"
                      : "bg-slate-800 text-slate-400"
                  }`}
                >
                  {ready?.index_ready ? "READY" : "NOT READY"}
                </span>
              </div>
              <button
                type="button"
                onClick={createIndex}
                disabled={indexing || ready?.index_ready}
                className="mt-5 w-full rounded-xl bg-indigo-400 px-4 py-3 text-sm font-bold text-slate-950 hover:bg-indigo-300 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
              >
                {indexing ? "PDF 임베딩 중..." : "RAG 인덱스 생성"}
              </button>
              <p className="mt-3 text-xs leading-5 text-slate-500">
                유효한 로컬 캐시가 있으면 문서를 다시 임베딩하지 않습니다. 캐시가
                없거나 원본·설정이 변경된 경우에만 OpenAI Embedding API가 호출됩니다.
              </p>
            </article>
          </div>

          <article className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6 shadow-2xl shadow-cyan-950/20">
            <p className="text-sm font-semibold text-cyan-300">Grounded answer</p>
            <h2 className="mt-2 text-xl font-bold">RAG 질의 테스트</h2>
            <form className="mt-6" onSubmit={submitQuestion}>
              <label className="block text-sm text-slate-400" htmlFor="question">
                사용자 질문
              </label>
              <textarea
                id="question"
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                rows="5"
                required
                placeholder="내 조건과 관련된 지원정책을 알려줘"
                className="mt-2 w-full resize-none rounded-xl border border-slate-700 bg-slate-950 p-4 text-sm outline-none focus:border-cyan-400"
              />
              <div className="mt-3 grid grid-cols-2 gap-3">
                <label className="text-sm text-slate-400">
                  Mock 사용자
                  <select
                    value={userId}
                    onChange={(event) => setUserId(event.target.value)}
                    className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100"
                  >
                    <option value="1">사용자 1 · 서울 · 음식점업</option>
                    <option value="2">사용자 2 · 부산 · 제조업</option>
                    <option value="3">사용자 3 · 일부 정보 누락</option>
                  </select>
                </label>
                <label className="text-sm text-slate-400">
                  검색 Chunk 수 (top_k)
                  <input
                    type="number"
                    min="1"
                    max="20"
                    value={topK}
                    onChange={(event) => setTopK(event.target.value)}
                    className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100"
                  />
                </label>
              </div>
              <button
                type="submit"
                disabled={answering || !ready?.index_ready || !question.trim()}
                className="mt-4 w-full rounded-xl bg-cyan-400 px-4 py-3 text-sm font-bold text-slate-950 hover:bg-cyan-300 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
              >
                {answering ? "근거 검색 및 답변 생성 중..." : "질문 전송"}
              </button>
            </form>

            {answer ? (
              <div className="mt-6 space-y-5 border-t border-slate-800 pt-6">
                <div>
                  <div className="mb-2 flex items-center gap-2">
                    <h3 className="font-bold">답변</h3>
                    <span
                      className={`rounded-full px-3 py-1 text-xs font-semibold ${
                        answer.grounded
                          ? "bg-emerald-100 text-emerald-700"
                          : "bg-amber-100 text-amber-700"
                      }`}
                    >
                      {answer.grounded ? "근거 있음" : "근거 부족"}
                    </span>
                  </div>
                  <p className="whitespace-pre-wrap text-sm leading-7 text-slate-200">
                    {answer.answer}
                  </p>
                </div>
                <div>
                  <h3 className="mb-3 font-bold">검색 근거</h3>
                  <ul className="space-y-3">
                    {answer.policies.map((policy) => (
                      <li
                        key={policy.policy_id}
                        className="rounded-xl border border-slate-800 bg-slate-950/70 p-4"
                      >
                        <div className="flex justify-between gap-3 text-sm font-semibold text-cyan-300">
                          <span>{policy.title}</span>
                          <span>policy {policy.policy_id}</span>
                        </div>
                        <ul className="mt-3 space-y-3">
                          {policy.sources.map((source) => (
                            <li key={source.chunk_id} className="border-t border-slate-800 pt-3">
                              <div className="flex justify-between gap-3 text-xs text-slate-500">
                                <span>{source.source} · {source.page}페이지</span>
                                <span>score {source.score.toFixed(4)}</span>
                              </div>
                              <p className="mt-2 text-sm leading-6 text-slate-300">
                                {source.excerpt}
                              </p>
                            </li>
                          ))}
                        </ul>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            ) : null}
          </article>
        </section>
      </div>
    </main>
  );
}

export default App;
