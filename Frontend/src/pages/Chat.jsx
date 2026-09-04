import { useEffect, useState } from "react";
import { api } from "../api.js";

const CATEGORIES = [
  ["tax", "세금"],
  ["expense", "경비"],
  ["saving", "절세"],
  ["policy", "지원정책"],
];

export default function Chat() {
  const [category, setCategory] = useState("tax");
  const [questions, setQuestions] = useState([]);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [sources, setSources] = useState([]);

  useEffect(() => {
    api.suggested(category).then((d) => setQuestions(d.questions || []));
    api.chatHistory(category).then((d) => {
      const rows = (d.messages || []).map((m) => ({
        role: "pair",
        question: m.question,
        answer: m.answer,
        messageId: m.id,
      }));
      setMessages(rows);
    });
  }, [category]);

  async function ask(question) {
    const text = question || input;
    if (!text.trim()) return;
    setInput("");
    const res = await api.sendChat({ category, question: text });
    setMessages((prev) => [
      ...prev,
      { role: "pair", question: text, answer: res.answer, messageId: res.messageId },
    ]);
    const src = await api.sources(res.messageId);
    setSources(src.sources || []);
  }

  return (
    <section className="max-w-3xl space-y-5">
      <header>
        <h2 className="text-2xl font-semibold">카테고리별 AI 상담</h2>
        <p className="text-ink/70">지금은 목업 답변입니다. 나중에 LLM 서비스만 교체하면 됩니다.</p>
      </header>
      <div className="flex gap-2">
        {CATEGORIES.map(([key, label]) => (
          <button
            key={key}
            onClick={() => setCategory(key)}
            className={`rounded-full px-4 py-1.5 text-sm ${
              category === key ? "bg-pine text-white" : "bg-white border border-sand"
            }`}
          >
            {label}
          </button>
        ))}
      </div>
      <div className="flex flex-wrap gap-2">
        {questions.map((q) => (
          <button key={q} onClick={() => ask(q)} className="rounded-full bg-sand px-3 py-1 text-sm">
            {q}
          </button>
        ))}
      </div>
      <div className="card space-y-4 p-5 min-h-72">
        {messages.map((m, i) => (
          <div key={i} className="space-y-2">
            <div className="rounded-2xl bg-pine text-white px-4 py-2 ml-12">{m.question}</div>
            <div className="rounded-2xl bg-paper px-4 py-3 mr-8 whitespace-pre-wrap text-sm">{m.answer}</div>
          </div>
        ))}
        {!messages.length && <p className="text-ink/50">추천 질문을 누르거나 직접 질문해 보세요.</p>}
      </div>
      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          ask();
        }}
      >
        <input
          className="flex-1 rounded-xl border border-sand px-3 py-2"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="질문을 입력하세요"
        />
        <button className="rounded-xl bg-pine px-4 text-white">보내기</button>
      </form>
      {!!sources.length && (
        <div className="text-sm text-ink/70">
          <p className="font-semibold text-ink">답변 근거(샘플)</p>
          {sources.map((s) => (
            <p key={s.url}>
              {s.title} — {s.excerpt}
            </p>
          ))}
        </div>
      )}
    </section>
  );
}
