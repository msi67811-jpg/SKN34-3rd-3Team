import { useEffect, useState } from "react";
import { api } from "../api.js";

const CATEGORIES = ["식비", "사무용품", "교통", "경조사비"];

export default function Expenses() {
  const [items, setItems] = useState([]);
  const [extraction, setExtraction] = useState(null);
  const [detail, setDetail] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [pickerKey, setPickerKey] = useState(0);

  async function load() {
    const data = await api.expenses();
    setItems(data.expenses || []);
  }

  useEffect(() => {
    load().catch((e) => setError(e.message));
  }, []);

  async function uploadFile(next) {
    if (!next) return;
    setLoading(true);
    setError("");
    setExtraction(null);
    try {
      const created = await api.uploadReceipt(next);
      const result = await api.receipt(created.receiptId);
      setExtraction({ ...result, receiptId: created.receiptId, status: created.status });
      setPickerKey((value) => value + 1);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function removeExpense(id) {
    setError("");
    try {
      await api.deleteExpense(id);
      if (extraction?.receiptId && items.find((item) => item.expenseId === id)?.receiptId === extraction.receiptId) {
        setExtraction(null);
      }
      if (detail?.expenseId === id) setDetail(null);
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function checkDeductibility(id) {
    setDetail(null);
    try {
      const data = await api.deductibility(id);
      setDetail({ expenseId: id, ...data });
    } catch (err) {
      setError(err.message);
    }
  }

  async function changeCategory(id, category) {
    try {
      const data = await api.updateExpense(id, { category });
      setDetail({ expenseId: id, ...data });
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section className="space-y-6">
      <header>
        <h2 className="text-2xl font-semibold">지출·영수증</h2>
        <p className="text-slate-400">
          영수증 사진을 Vision OCR로 읽고, 분류를 수정한 뒤 경비 가능성을 확인할 수 있습니다.
        </p>
      </header>

      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
        <p className="mb-1 text-xs text-white">영수증 이미지</p>
        <label className="relative inline-flex cursor-pointer rounded-lg bg-white/20 px-3 py-1.5 text-sm text-white">
          {loading ? "이미지 분석 중..." : "이미지 선택"}
          <input
            key={pickerKey}
            type="file"
            accept="image/*"
            disabled={loading}
            className="absolute inset-0 cursor-pointer opacity-0"
            onChange={(e) => uploadFile(e.target.files?.[0] || null)}
          />
        </label>
      </div>

      {extraction && (
        <div className="relative rounded-2xl border border-slate-800 bg-slate-900/60 p-5 pr-10 text-sm text-white">
          <button
            type="button"
            className="absolute right-3 top-3 text-lg leading-none text-white"
            title="삭제"
            onClick={() => {
              const match = items.find((item) => item.receiptId === extraction.receiptId);
              if (match) removeExpense(match.expenseId);
              else setExtraction(null);
            }}
          >
            ×
          </button>
          <h3 className="font-semibold text-white">추출 결과</h3>
          <p className="mt-2">영수증 #{extraction.receiptId}</p>
          <p className="mt-1">날짜: {String(extraction.date).slice(0, 10)}</p>
          <p>상호: {extraction.vendor}</p>
          <p>금액: {Number(extraction.amount).toLocaleString()}원</p>
          <p className="mt-1 text-white">품목: {(extraction.items || []).join(", ")}</p>
        </div>
      )}

      <ul className="space-y-2">
        {items.map((item) => (
          <li
            key={item.expenseId}
            className="relative flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-800 bg-slate-900/60 px-4 py-3 pr-10 text-sm text-white"
          >
            <button
              type="button"
              className="absolute right-3 top-2 text-lg leading-none text-white"
              title="삭제"
              onClick={() => removeExpense(item.expenseId)}
            >
              ×
            </button>
            <div>
              <p className="font-medium text-white">
                {item.category} · {Number(item.amount).toLocaleString()}원
              </p>
              <p className="text-xs text-white">
                {String(item.date).slice(0, 10)} · 영수증 #{item.receiptId} ·{" "}
                {item.deductible ? "경비 가능" : "확인 필요"}
                {item.items?.length ? ` · 품목: ${item.items.join(", ")}` : ""}
              </p>
              <select
                className="mt-2 rounded-lg border border-slate-700 bg-slate-950 px-2 py-1 text-xs text-white"
                value={item.category}
                onChange={(e) => changeCategory(item.expenseId, e.target.value)}
              >
                {CATEGORIES.map((category) => (
                  <option key={category}>{category}</option>
                ))}
              </select>
            </div>
            <button className="text-cyan-300 underline" onClick={() => checkDeductibility(item.expenseId)}>
              경비 판정
            </button>
          </li>
        ))}
        {!items.length && <li className="text-slate-500">등록된 지출이 없습니다. 영수증을 업로드해 보세요.</li>}
      </ul>

      {detail && (
        <div className="rounded-2xl border border-slate-800 bg-slate-950/80 p-5 text-sm text-slate-300">
          <p>
            지출 #{detail.expenseId}:{" "}
            <span className={detail.deductible ? "text-emerald-300" : "text-amber-300"}>
              {detail.deductible ? "인정 가능" : "인정 어려움"}
            </span>
            {detail.llmUsed ? " · RAG 설명" : " · 규칙 안내"}
          </p>
          <p className="mt-1 text-slate-500">신뢰도 {(detail.confidence * 100).toFixed(0)}%</p>
          <p className="mt-2 whitespace-pre-wrap">{detail.basis}</p>
          {!!detail.sources?.length && (
            <p className="mt-2 text-xs text-slate-500">근거: {detail.sources.join(", ")}</p>
          )}
        </div>
      )}

      {error ? <p className="text-sm text-rose-300">{error}</p> : null}
    </section>
  );
}
