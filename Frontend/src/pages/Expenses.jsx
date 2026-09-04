import { useEffect, useState } from "react";
import { api } from "../api.js";

export default function Expenses() {
  const [items, setItems] = useState([]);
  const [selected, setSelected] = useState(null);
  const [analysis, setAnalysis] = useState(null);

  async function reload() {
    const data = await api.expenses();
    setItems(data.expenses || []);
  }

  useEffect(() => {
    reload();
  }, []);

  async function upload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    const created = await api.uploadReceipt(file);
    const extracted = await api.receipt(created.receiptId);
    setSelected(extracted);
    await reload();
  }

  async function analyze(id) {
    setAnalysis(await api.deductibility(id));
  }

  return (
    <section className="max-w-2xl space-y-5">
      <h2 className="text-2xl font-semibold">지출 · 영수증</h2>
      <p className="text-ink/70">업로드하면 OCR 대신 샘플 추출 결과가 채워집니다.</p>
      <input type="file" accept="image/*" onChange={upload} />
      {selected && (
        <div className="card p-5 text-sm">
          <p><b>상호</b> {selected.vendor}</p>
          <p><b>금액</b> {selected.amount.toLocaleString()}원</p>
          <p><b>항목</b> {selected.items.join(", ")}</p>
        </div>
      )}
      <div className="card divide-y divide-sand">
        {items.map((e) => (
          <button key={e.expenseId} className="flex w-full justify-between p-4 text-left text-sm" onClick={() => analyze(e.expenseId)}>
            <span>{e.category} · {e.amount.toLocaleString()}원</span>
            <span className="text-ink/50">{e.deductible ? "경비 가능" : "검토 필요"}</span>
          </button>
        ))}
        {!items.length && <p className="p-4 text-ink/50">아직 지출이 없습니다.</p>}
      </div>
      {analysis && (
        <div className="card p-5 text-sm">
          <p>인정 가능성 {Math.round(analysis.confidence * 100)}%</p>
          <p className="mt-1 text-ink/70">{analysis.basis}</p>
        </div>
      )}
    </section>
  );
}
