import { useEffect, useState } from "react";
import { api } from "../api.js";

const CATEGORIES = [
  { id: "tax", label: "세금" },
  { id: "expense", label: "경비" },
  { id: "saving", label: "절세" },
  { id: "policy", label: "정책" },
];

const field =
  "w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100";

export default function Chat() {
  const [category, setCategory] = useState("tax");
  const [suggested, setSuggested] = useState([]);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sources, setSources] = useState([]);
  const [error, setError] = useState("");
  const [meta, setMeta] = useState({ llmUsed: false, grounded: false, needsConfirmation: false });

  async function loadHistory(cat = category) {
    const data = await api.chatHistory(cat);
    setMessages(data.messages || []);
  }

  useEffect(() => {
    api.suggested(category).then((d) => setSuggested(d.questions || []));
    loadHistory(category);
    setSources([]);
  }, [category]);

  async function ask(question) {
    const q = question.trim();
    if (!q) return;
    setLoading(true);
    setSources([]);
    setError("");
    setMeta({ llmUsed: false, grounded: false, needsConfirmation: false });
    try {
      const data = await api.sendChat({ category, question: q });
      setInput("");
      setMeta({
        llmUsed: Boolean(data.llmUsed),
        grounded: Boolean(data.grounded),
        needsConfirmation: Boolean(data.needsConfirmation),
      });
      await loadHistory(category);
      if (data.messageId) {
        const src = await api.sources(data.messageId);
        setSources(src.sources || []);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="grid gap-4 lg:grid-cols-[220px_1fr]">
      <aside className="space-y-4 rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
        <h2 className="font-semibold">카테고리</h2>
        <div className="space-y-1">
          {CATEGORIES.map((c) => (
            <button
              key={c.id}
              className={`block w-full rounded-lg px-3 py-2 text-left text-sm ${
                category === c.id ? "bg-cyan-500/20 text-cyan-100" : "text-slate-300 hover:bg-slate-800"
              }`}
              onClick={() => setCategory(c.id)}
            >
              {c.label}
            </button>
          ))}
        </div>
        <div>
          <p className="mb-2 text-xs text-slate-500">추천 질문</p>
          <ul className="space-y-1">
            {suggested.map((q) => (
              <li key={q}>
                <button
                  className="w-full rounded-lg bg-slate-950/80 px-2 py-1.5 text-left text-xs text-slate-300 hover:text-cyan-200"
                  onClick={() => ask(q)}
                >
                  {q}
                </button>
              </li>
            ))}
          </ul>
        </div>
        <p className="text-xs text-slate-500">
          Backend가 LLM RAG(`8001`)를 호출합니다. 서비스가 꺼져 있으면 목업 답변으로 대체됩니다.
        </p>
        {meta.needsConfirmation && (
          <p className="text-xs text-amber-300">근거가 부족합니다. 원문·전문가 확인이 필요합니다.</p>
        )}
        {meta.llmUsed && !meta.needsConfirmation && (
          <p className="text-xs text-emerald-300">
            {meta.grounded ? "근거 기반 RAG 답변" : "LLM 응답"}
          </p>
        )}
        {!sources.length && meta.needsConfirmation && (
          <p className="text-xs text-slate-500">샘플 출처를 붙이지 않았습니다.</p>
        )}
      </aside>

      <div className="flex min-h-[70vh] flex-col rounded-2xl border border-slate-800 bg-slate-900/60">
        <div className="flex items-center justify-between border-b border-slate-800 px-5 py-3">
          <p className="text-sm text-slate-300">대화 기록</p>
          <button
            type="button"
            disabled={!messages.length || loading}
            className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-rose-300 hover:bg-slate-800 disabled:opacity-40"
            onClick={async () => {
              if (!window.confirm("이 카테고리 대화 기록을 모두 지울까요?")) return;
              try {
                await api.clearChat(category);
                setMessages([]);
                setSources([]);
                setError("");
                setMeta({ llmUsed: false, grounded: false, needsConfirmation: false });
              } catch (err) {
                setError(err.message);
              }
            }}
          >
            대화 기록 초기화
          </button>
        </div>
        <div className="flex-1 space-y-3 overflow-y-auto p-5">
          {messages.map((m) => (
            <div key={m.id || m.messageId} className="space-y-2">
              {m.question && (
                <div className="ml-auto max-w-[85%] rounded-2xl bg-cyan-500/20 px-4 py-3 text-sm text-cyan-50">
                  {m.question}
                </div>
              )}
              {m.answer && (
                <div className="max-w-[85%] whitespace-pre-wrap rounded-2xl bg-slate-950 px-4 py-3 text-sm text-slate-200">
                  {m.answer}
                </div>
              )}
            </div>
          ))}
          {!messages.length && (
            <p className="text-slate-500">추천 질문을 누르거나 직접 입력해 보세요.</p>
          )}
          {error && <p className="text-sm text-rose-300">{error}</p>}
          {sources.length > 0 && (
            <div className="rounded-xl border border-slate-700 bg-slate-950/80 p-3 text-xs text-slate-400">
              <p className="mb-2 font-medium text-slate-300">근거 문서</p>
              <ul className="space-y-2">
                {sources.map((s, i) => (
                  <li key={i}>
                    <a className="text-cyan-300 underline" href={s.url} target="_blank" rel="noreferrer">
                      {s.title}
                    </a>
                    <p className="mt-1">{s.excerpt}</p>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
        <form
          className="flex gap-2 border-t border-slate-800 p-4"
          onSubmit={(e) => {
            e.preventDefault();
            ask(input);
          }}
        >
          <input
            className={field}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="세금·정책 질문을 입력하세요"
          />
          <button
            disabled={loading}
            className="rounded-xl bg-cyan-500 px-4 font-semibold text-slate-950 disabled:opacity-50"
          >
            {loading ? "..." : "전송"}
          </button>
        </form>
      </div>
    </section>
  );
}
