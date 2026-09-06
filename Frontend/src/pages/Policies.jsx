import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";

const field = "rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-white placeholder:text-slate-400";

function MatchScore({ policy }) {
  if (policy.matchScore == null) return null;
  return (
    <span className="ml-2 text-xs font-medium text-black">
      적합 {policy.matchScore}점{policy.eligible ? " · 자격 충족" : ""}
    </span>
  );
}

function PolicyTitle({ policy, large = false }) {
  return (
    <Link
      className={`${large ? "text-lg font-medium" : ""} text-[#1f6b4f] underline`}
      to={`/policies/${policy.policyId}`}
    >
      {policy.title}
    </Link>
  );
}

export default function Policies() {
  const [keyword, setKeyword] = useState("");
  const [region, setRegion] = useState("");
  const [industry, setIndustry] = useState("");
  const [items, setItems] = useState([]);
  const [recommended, setRecommended] = useState([]);
  const [saved, setSaved] = useState([]);

  async function search() {
    const data = await api.policies({
      keyword: keyword || undefined,
      region: region || undefined,
      industry: industry || undefined,
    });
    setItems(data.policies || []);
  }

  useEffect(() => {
    search();
    api.recommend().then((d) => setRecommended(d.policies || []));
    api.savedPolicies().then((d) => setSaved(d.policies || [])).catch(() => {});
  }, []);

  return (
    <section className="space-y-6">
      <header>
        <h2 className="text-2xl font-semibold">정책 탐색</h2>
        <p className="text-slate-400">지역·키워드·업종으로 지원 정책을 검색합니다.</p>
      </header>

      <div className="flex flex-wrap gap-2">
        <input className={field} placeholder="키워드" value={keyword} onChange={(e) => setKeyword(e.target.value)} />
        <input className={field} placeholder="지역" value={region} onChange={(e) => setRegion(e.target.value)} />
        <input className={field} placeholder="업종" value={industry} onChange={(e) => setIndustry(e.target.value)} />
        <button className="rounded-xl bg-cyan-500 px-4 font-semibold text-slate-950" onClick={search}>
          검색
        </button>
      </div>

      <div className="ui-card p-5">
        <h3 className="font-semibold">맞춤 추천</h3>
        <ul className="mt-3 grid gap-2 sm:grid-cols-2">
          {recommended.map((p) => (
            <li key={p.policyId}>
              <PolicyTitle policy={p} />
              <MatchScore policy={p} />
            </li>
          ))}
          {!recommended.length && <li className="text-neutral-500">내 사업 정보를 입력하면 추천이 표시됩니다.</li>}
        </ul>
      </div>

      {saved.length > 0 && (
        <div className="ui-card p-5">
          <h3 className="font-semibold">관심 정책</h3>
          <ul className="mt-3 grid gap-2 sm:grid-cols-2">
            {saved.map((p) => (
              <li key={p.policyId}>
                <PolicyTitle policy={p} />
                <MatchScore policy={p} />
              </li>
            ))}
          </ul>
        </div>
      )}

      <ul className="space-y-3">
        {items.map((p) => (
          <li key={p.policyId} className="ui-card p-5">
            <div>
              <PolicyTitle policy={p} large />
              <MatchScore policy={p} />
            </div>
            <p className="mt-2 text-sm text-black">{p.benefit}</p>
            <p className="mt-2 text-xs font-medium text-black">
              {p.region} · {p.industry} · {p.target} · 마감 {String(p.applyEndDate || "").slice(0, 10) || "-"}
            </p>
          </li>
        ))}
        {!items.length && <li className="text-neutral-500">검색 결과가 없습니다.</li>}
      </ul>
    </section>
  );
}
