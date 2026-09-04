import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";

export default function Policies() {
  const [keyword, setKeyword] = useState("");
  const [region, setRegion] = useState("");
  const [items, setItems] = useState([]);

  async function load() {
    const data = await api.policies({
      ...(keyword ? { keyword } : {}),
      ...(region ? { region } : {}),
    });
    setItems(data.policies || []);
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <section className="space-y-5">
      <h2 className="text-2xl font-semibold">지원정책</h2>
      <form
        className="flex flex-wrap gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          load();
        }}
      >
        <input className="rounded-xl border border-sand px-3 py-2" placeholder="키워드" value={keyword} onChange={(e) => setKeyword(e.target.value)} />
        <input className="rounded-xl border border-sand px-3 py-2" placeholder="지역 (예: 서울)" value={region} onChange={(e) => setRegion(e.target.value)} />
        <button className="rounded-xl bg-pine px-4 text-white">검색</button>
      </form>
      <div className="grid gap-4 md:grid-cols-2">
        {items.map((p) => (
          <Link key={p.policyId} to={`/policies/${p.policyId}`} className="card p-5 hover:border-pine">
            <p className="text-xs text-moss">{p.region} · {p.source}</p>
            <h3 className="mt-1 text-lg font-semibold">{p.title}</h3>
            <p className="mt-2 text-sm text-ink/70">{p.benefit}</p>
            <p className="mt-3 text-xs text-ink/50">마감 {p.applyEndDate || "-"}</p>
          </Link>
        ))}
      </div>
    </section>
  );
}
